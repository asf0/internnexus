"""HTTP client and provider dispatch for classification."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, NoReturn

import httpx
from internnexus_core.embedding import OPENAI_COMPATIBLE_PROVIDER, normalize_embedding_provider
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from pipeline.classification.parser import (
    _extract_batch_categories,
    _extract_canonical_category,
)
from pipeline.classification.prompts import (
    _build_batch_classification_prompts,
    _build_classification_prompts,
)
from pipeline.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 90.0
MAX_CONCURRENT_REQUESTS = 2


class ClassificationError(Exception):
    """Base exception for classification failures."""

    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class RateLimitError(ClassificationError):
    """Rate limit exceeded - retryable."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message, retryable=True)
        self.retry_after = retry_after


def _is_retryable_exception(exc: BaseException) -> bool:
    """Determine if an exception is retryable."""
    if isinstance(exc, asyncio.CancelledError):
        return False
    if isinstance(exc, ClassificationError):
        return exc.retryable
    if isinstance(exc, (httpx.RequestError, httpx.TimeoutException)):
        return True
    return False


_retry_decorator = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception(lambda e: _is_retryable_exception(e)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


class ClassificationClient:
    """Low-level async client for Ollama and OpenAI-compatible classification APIs."""

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        provider: str | None = None,
        timeout: float | None = None,
        max_concurrent: int | None = None,
        settings: Any | None = None,
    ) -> None:
        if settings is None:
            settings = get_settings()
        self._model = model or settings.resolved_classification_model
        classification_url = settings.openai_classification_url or settings.openai_base_url
        self._base_url = (base_url or classification_url).rstrip("/")
        configured_timeout = float(getattr(settings, "classification_timeout_seconds", DEFAULT_TIMEOUT))
        configured_concurrency = int(getattr(settings, "classification_max_concurrent", MAX_CONCURRENT_REQUESTS))
        self._timeout = float(timeout) if timeout is not None else configured_timeout
        self._max_concurrent = int(max_concurrent) if max_concurrent is not None else configured_concurrency
        self.batch_size = int(getattr(settings, "classification_batch_size", 10))
        self.max_concurrent = self._max_concurrent
        self._keep_alive = str(getattr(settings, "classification_keep_alive", "30m"))
        self._num_predict = int(getattr(settings, "classification_num_predict", 20))
        self._client: httpx.AsyncClient | None = None
        self._provider = normalize_embedding_provider(provider or settings.embedding_provider)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(self._timeout, connect=10.0))
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def classify_job_with_reason(self, title: str, description: str) -> tuple[str | None, str, str]:
        """Classify a single job and return category, reason, and raw output sample."""
        try:
            if self._provider == OPENAI_COMPATIBLE_PROVIDER:
                return await self._classify_openai_compatible(title, description)
            return await self._classify_ollama(title, description)
        except asyncio.CancelledError:
            logger.warning("Classification request cancelled")
            raise
        except ClassificationError as e:
            logger.warning("Classification failed for '%s': %s", title, e)
            return None, "http_or_timeout_error", ""
        except Exception as e:  # noqa: BLE001  # single-job failure should not crash the batch
            logger.error("Unexpected classification error for '%s': %s", title, e)
            return None, "unexpected_error", ""

    async def _classify_ollama(self, title: str, description: str) -> tuple[str | None, str, str]:
        return await self._classify_ollama_impl(title, description)

    @_retry_decorator
    async def _classify_ollama_impl(self, title: str, description: str) -> tuple[str | None, str, str]:
        system_prompt, user_prompt = _build_classification_prompts(title, description)
        prompt = f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}"
        client = await self._get_client()

        try:
            response = await client.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": self._keep_alive,
                    "options": {
                        "temperature": 0.0,
                        "num_predict": self._num_predict,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
        except asyncio.CancelledError:
            raise
        except httpx.TimeoutException as exc:
            raise ClassificationError(
                f"Ollama classification timed out for '{title}': {exc}",
                retryable=True,
            ) from exc
        except httpx.RequestError as exc:
            raise ClassificationError(
                f"Ollama connection failed for '{title}': {exc}",
                retryable=True,
            ) from exc
        except httpx.HTTPStatusError as exc:
            self._handle_http_error(exc, title, "Ollama")

        raw_output = data.get("response", "")
        category, reason = _extract_canonical_category(raw_output)
        return category, reason, raw_output

    async def _classify_openai_compatible(self, title: str, description: str) -> tuple[str | None, str, str]:
        return await self._classify_openai_compatible_impl(title, description)

    @_retry_decorator
    async def _classify_openai_compatible_impl(self, title: str, description: str) -> tuple[str | None, str, str]:
        system_prompt, user_prompt = _build_classification_prompts(title, description)
        client = await self._get_client()

        try:
            response = await client.post(
                f"{self._base_url}/v1/chat/completions",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.0,
                    "max_tokens": 32,
                },
            )
            response.raise_for_status()
            data = response.json()
        except asyncio.CancelledError:
            raise
        except httpx.TimeoutException as exc:
            raise ClassificationError(
                f"OpenAI-compatible API classification timed out for '{title}': {exc}",
                retryable=True,
            ) from exc
        except httpx.RequestError as exc:
            raise ClassificationError(
                f"OpenAI-compatible API connection failed for '{title}': {exc}",
                retryable=True,
            ) from exc
        except httpx.HTTPStatusError as exc:
            self._handle_http_error(exc, title, "OpenAI-compatible API")

        choices = data.get("choices", [])
        if not choices:
            logger.warning("No choices in OpenAI-compatible API response for '%s'", title)
            return None, "empty_response", ""

        message = choices[0].get("message", {})
        raw_output = message.get("content", "")
        category, reason = _extract_canonical_category(raw_output)
        return category, reason, raw_output

    async def classify_prompt_batch_with_reasons(
        self,
        jobs: list[tuple[str, str]],
    ) -> list[tuple[str | None, str, str]]:
        if not jobs:
            return []
        if self._provider == OPENAI_COMPATIBLE_PROVIDER:
            return await self._classify_openai_compatible_batch(jobs)
        return await self._classify_ollama_batch(jobs)

    async def _classify_ollama_batch(self, jobs: list[tuple[str, str]]) -> list[tuple[str | None, str, str]]:
        return await self._classify_ollama_batch_impl(jobs)

    @_retry_decorator
    async def _classify_ollama_batch_impl(self, jobs: list[tuple[str, str]]) -> list[tuple[str | None, str, str]]:
        system_prompt, user_prompt = _build_batch_classification_prompts(jobs)
        prompt = f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}"
        client = await self._get_client()

        try:
            response = await client.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": self._keep_alive,
                    "options": {
                        "temperature": 0.0,
                        "num_predict": max(self._num_predict, 24 * len(jobs)),
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
        except asyncio.CancelledError:
            raise
        except httpx.TimeoutException as exc:
            raise ClassificationError(
                f"Ollama batch classification timed out for {len(jobs)} jobs: {exc}",
                retryable=True,
            ) from exc
        except httpx.RequestError as exc:
            raise ClassificationError(
                f"Ollama batch classification connection failed for {len(jobs)} jobs: {exc}",
                retryable=True,
            ) from exc
        except httpx.HTTPStatusError as exc:
            self._handle_http_error(exc, f"batch:{len(jobs)}", "Ollama")

        raw_output = data.get("response", "")
        return _extract_batch_categories(raw_output, len(jobs))

    async def _classify_openai_compatible_batch(self, jobs: list[tuple[str, str]]) -> list[tuple[str | None, str, str]]:
        return await self._classify_openai_compatible_batch_impl(jobs)

    @_retry_decorator
    async def _classify_openai_compatible_batch_impl(
        self, jobs: list[tuple[str, str]]
    ) -> list[tuple[str | None, str, str]]:
        system_prompt, user_prompt = _build_batch_classification_prompts(jobs)
        client = await self._get_client()

        try:
            response = await client.post(
                f"{self._base_url}/v1/chat/completions",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.0,
                    "max_tokens": max(128, 24 * len(jobs)),
                },
            )
            response.raise_for_status()
            data = response.json()
        except asyncio.CancelledError:
            raise
        except httpx.TimeoutException as exc:
            raise ClassificationError(
                f"OpenAI-compatible API batch classification timed out for {len(jobs)} jobs: {exc}",
                retryable=True,
            ) from exc
        except httpx.RequestError as exc:
            raise ClassificationError(
                f"OpenAI-compatible API batch classification connection failed for {len(jobs)} jobs: {exc}",
                retryable=True,
            ) from exc
        except httpx.HTTPStatusError as exc:
            self._handle_http_error(exc, f"batch:{len(jobs)}", "OpenAI-compatible API")

        choices = data.get("choices", [])
        if not choices:
            return [(None, "empty_response", "")] * len(jobs)

        message = choices[0].get("message", {})
        raw_output = message.get("content", "")
        return _extract_batch_categories(raw_output, len(jobs))

    async def classify_batch_individually_with_reasons(
        self,
        jobs: list[tuple[str, str]],
    ) -> list[tuple[str | None, str, str]]:
        results: list[tuple[str | None, str, str]] = []
        for title, description in jobs:
            try:
                results.append(await self.classify_job_with_reason(title, description))
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001  # per-job fallback: one failed job should not stop the rest
                logger.error("Error classifying job '%s': %s", title, exc)
                results.append((None, "unexpected_error", ""))
        return results

    def _handle_http_error(self, exc: httpx.HTTPStatusError, title: str, provider: str) -> NoReturn:
        """Handle HTTP status errors."""
        status_code = exc.response.status_code if exc.response else 0
        detail = exc.response.text[:500] if exc.response is not None else ""

        if status_code == 429:
            retry_after = None
            if exc.response and "retry-after" in exc.response.headers:
                try:
                    retry_after = float(exc.response.headers["retry-after"])
                except (ValueError, TypeError):
                    pass
            raise RateLimitError(
                f"{provider} rate limited. Retry-After: {retry_after}",
                retry_after=retry_after,
            ) from exc
        if status_code >= 500:
            raise ClassificationError(
                f"{provider} server error ({status_code}) for '{title}': {detail}",
                retryable=True,
            ) from exc
        raise ClassificationError(
            f"{provider} request failed ({status_code}) for '{title}': {detail}",
            retryable=False,
        ) from exc
