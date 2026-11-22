"""OpenAI-compatible HTTP client for classification."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, NoReturn

import httpx

from pipeline.stages.classification.response_parser import (
    _extract_batch_categories,
    _extract_canonical_category,
)
from pipeline.stages.classification.prompts import (
    _build_batch_classification_prompts,
    _build_classification_prompts,
)
from pipeline.infra.async_retry import RetryPolicy, with_retry
from pipeline.infra.settings import get_settings

logger = logging.getLogger(__name__)
_TIMED_OUT = "timed out"


_PROVIDER = "OpenAI-compatible API"
_CHAT_ENDPOINT = "chat/completions"


def _extract_openai_text(response: dict[str, Any]) -> str | None:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return None
    message = first_choice.get("message")
    if not isinstance(message, dict):
        return None
    raw_output = message.get("content", "")
    return raw_output if isinstance(raw_output, str) else ""


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


_CLASSIFICATION_RETRY_POLICY = RetryPolicy(
    max_attempts=3,
    base_delay=1,
    max_delay=10,
)


class ClassificationClient:
    """Low-level async client for OpenAI-compatible classification APIs."""

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        max_concurrent: int | None = None,
        settings: Any | None = None,
    ) -> None:
        if settings is None:
            settings = get_settings()
        self._model = model or settings.resolved_classification_model
        classification_url = settings.openai_classification_url or settings.openai_base_url
        self._base_url = (base_url or classification_url).rstrip("/")
        self._timeout = float(timeout) if timeout is not None else float(settings.classification_timeout_seconds)
        self._max_concurrent = (
            int(max_concurrent) if max_concurrent is not None else int(settings.classification_max_concurrent)
        )
        self.batch_size = int(settings.classification_batch_size)
        self.max_concurrent = self._max_concurrent
        self._temperature = float(settings.classification_temperature)
        self._openai_max_tokens = int(settings.classification_openai_max_tokens)
        self._openai_batch_min_tokens = int(settings.classification_openai_batch_min_tokens)
        self._openai_batch_tokens_per_job = int(settings.classification_openai_batch_tokens_per_job)
        self._parse_retry_attempts = int(settings.classification_parse_retry_attempts)
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(self._timeout, connect=10.0))
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _endpoint_url(self, endpoint: str) -> str:
        """Join an endpoint to either an API root or an existing ``/v1`` base."""
        suffix = endpoint.lstrip("/")
        if self._base_url.endswith("/v1"):
            return f"{self._base_url}/{suffix}"
        return f"{self._base_url}/v1/{suffix}"

    async def classify_job_with_reason(self, title: str, description: str) -> tuple[str | None, str, str]:
        """Classify a single job and return category, reason, and raw output sample.

        Retries when a request succeeds but the response doesn't parse into a
        category: this provider is not fully deterministic even at
        temperature 0 (continuous batching/speculative decoding introduces
        sampling variance), so a failed parse is often resolved by a fresh
        attempt rather than a persistent problem.
        """
        result: tuple[str | None, str, str] = (None, "empty_response", "")
        for _attempt in range(self._parse_retry_attempts + 1):
            try:
                result = await self._classify_openai_compatible(title, description)
            except asyncio.CancelledError:
                logger.warning("Classification request cancelled")
                raise
            except ClassificationError as e:
                logger.warning("Classification failed for '%s': %s", title, e)
                return None, "http_or_timeout_error", ""
            except Exception:  # noqa: BLE001  # single-job failure should not crash the batch
                logger.exception("Unexpected classification error for '%s'", title)
                return None, "unexpected_error", ""
            if result[0] is not None:
                return result
        return result

    async def _classify_openai_compatible(self, title: str, description: str) -> tuple[str | None, str, str]:
        system_prompt, user_prompt = _build_classification_prompts(title, description)
        raw_output = await self._request_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            request_label=title,
            token_budget=self._openai_max_tokens,
        )
        if raw_output is None:
            logger.warning("No choices in OpenAI-compatible API response for '%s'", title)
            return None, "empty_response", ""

        category, reason = _extract_canonical_category(raw_output)
        return category, reason, raw_output

    async def classify_prompt_batch_with_reasons(
        self,
        jobs: list[tuple[str, str]],
    ) -> list[tuple[str | None, str, str]]:
        if not jobs:
            return []
        system_prompt, user_prompt = _build_batch_classification_prompts(jobs)
        raw_output = await self._request_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            request_label=f"batch:{len(jobs)}",
            token_budget=max(self._openai_batch_min_tokens, self._openai_batch_tokens_per_job * len(jobs)),
        )
        if raw_output is None:
            return [(None, "empty_response", "")] * len(jobs)

        return _extract_batch_categories(raw_output, len(jobs))

    async def _request_text(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        request_label: str,
        token_budget: int,
    ) -> str | None:
        """Execute one provider request and extract its response text."""

        async def request_once() -> str | None:
            client = self._get_client()
            try:
                response = await client.post(
                    self._endpoint_url(_CHAT_ENDPOINT),
                    json={
                        "model": self._model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": self._temperature,
                        "max_tokens": token_budget,
                    },
                )
                response.raise_for_status()
                data = response.json()
            except asyncio.CancelledError:
                raise
            except httpx.TimeoutException as exc:
                raise ClassificationError(
                    self._request_error_message(request_label, _TIMED_OUT, exc),
                    retryable=True,
                ) from exc
            except httpx.RequestError as exc:
                raise ClassificationError(
                    self._request_error_message(request_label, "connection failed", exc),
                    retryable=True,
                ) from exc
            except httpx.HTTPStatusError as exc:
                self._handle_http_error(exc, request_label)

            if not isinstance(data, dict):
                return None
            return _extract_openai_text(data)

        def log_retry(exc: BaseException, attempt: int, delay: float) -> None:
            logger.warning(
                "Retrying %s classification request after attempt %d in %.1fs: %s",
                _PROVIDER,
                attempt,
                delay,
                exc,
            )

        return await with_retry(
            request_once,
            policy=_CLASSIFICATION_RETRY_POLICY,
            retryable=_is_retryable_exception,
            sleep=asyncio.sleep,
            before_sleep=log_retry,
        )

    @staticmethod
    def _request_error_message(request_label: str, failure: str, exc: BaseException) -> str:
        if request_label.startswith("batch:"):
            count = request_label.removeprefix("batch:")
            if failure == _TIMED_OUT:
                return f"{_PROVIDER} batch classification timed out for {count} jobs: {exc}"
            return f"{_PROVIDER} batch classification connection failed for {count} jobs: {exc}"
        if failure == _TIMED_OUT:
            return f"{_PROVIDER} classification timed out for '{request_label}': {exc}"
        return f"{_PROVIDER} connection failed for '{request_label}': {exc}"

    def _handle_http_error(self, exc: httpx.HTTPStatusError, title: str) -> NoReturn:
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
                f"{_PROVIDER} rate limited. Retry-After: {retry_after}",
                retry_after=retry_after,
            ) from exc
        if status_code >= 500:
            raise ClassificationError(
                f"{_PROVIDER} server error ({status_code}) for '{title}': {detail}",
                retryable=True,
            ) from exc
        raise ClassificationError(
            f"{_PROVIDER} request failed ({status_code}) for '{title}': {detail}",
            retryable=False,
        ) from exc
