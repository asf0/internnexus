"""LLM-based job classification service using Ollama or LM Studio."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from pipeline.backend_bridge import get_settings
from pipeline.category_mapping import CANONICAL_CATEGORIES, get_canonical_category

logger = logging.getLogger(__name__)

# Default timeout for classification requests (seconds)
DEFAULT_TIMEOUT = 30.0

# Maximum concurrent requests for batch processing
MAX_CONCURRENT_REQUESTS = 5

# Maximum description length to send to LLM (chars)
MAX_DESCRIPTION_LENGTH = 500

# Valid category pattern (lowercase letters, numbers, underscores)
VALID_CATEGORY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

# Use all canonical categories - LLM must choose from this exact list
VALID_CATEGORIES = CANONICAL_CATEGORIES


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


def _build_classification_prompt(title: str, description: str) -> str:
    """Build the classification prompt for the LLM."""
    truncated_desc = description[:MAX_DESCRIPTION_LENGTH]
    if len(description) > MAX_DESCRIPTION_LENGTH:
        truncated_desc += "..."

    categories_str = ", ".join(VALID_CATEGORIES)

    prompt = f"""Classify this job into ONE category. You MUST output ONLY one of these exact category slugs (lowercase, underscores):
{categories_str}

Title: {title}
Description: {truncated_desc}

Category:"""

    return prompt


def _normalize_category(raw_output: str) -> str | None:
    """Normalize and validate the LLM output to a canonical category slug."""
    if not raw_output:
        return None

    # Strip whitespace
    category = raw_output.strip()

    # Remove any quotes or extra formatting
    category = category.strip("\"'")

    # Convert to lowercase
    category = category.lower()

    # Replace spaces and hyphens with underscores
    category = re.sub(r"[\s\-]+", "_", category)

    # Remove any non-alphanumeric characters except underscores
    category = re.sub(r"[^a-z0-9_]", "", category)

    # Remove leading/trailing underscores
    category = category.strip("_")

    # Remove consecutive underscores
    category = re.sub(r"_+", "_", category)

    # Validate the format
    if not category or not VALID_CATEGORY_PATTERN.match(category):
        return None

    # Map to canonical category
    canonical = get_canonical_category(category)
    return canonical


class JobClassifier:
    """Async job classification service supporting Ollama and LM Studio."""

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        provider: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_concurrent: int = MAX_CONCURRENT_REQUESTS,
    ) -> None:
        """Initialize the classifier.

        Args:
            model: Model name (defaults to settings.classification_model)
            base_url: API URL (defaults to settings.resolved_classification_url)
            provider: "ollama" or "lmstudio" (defaults to settings.embedding_provider)
            timeout: Request timeout in seconds
            max_concurrent: Maximum concurrent requests for batch processing
        """
        settings = get_settings()
        self._model = model or settings.classification_model
        self._base_url = (base_url or settings.resolved_classification_url).rstrip("/")
        self._provider = provider or settings.embedding_provider
        self._timeout = timeout
        self._max_concurrent = max_concurrent
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def classify_job(self, title: str, description: str) -> str | None:
        """Classify a single job into a category.

        Args:
            title: Job title
            description: Job description text

        Returns:
            Category slug (e.g., "software_engineering") or None if classification fails
        """
        try:
            if self._provider == "lmstudio":
                return await self._classify_lmstudio(title, description)
            else:
                return await self._classify_ollama(title, description)
        except asyncio.CancelledError:
            logger.warning("Classification request cancelled")
            raise
        except ClassificationError as e:
            logger.warning(f"Classification failed for '{title}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected classification error for '{title}': {e}")
            return None

    async def _classify_ollama(self, title: str, description: str) -> str | None:
        """Classify using Ollama native API."""
        return await self._classify_ollama_impl(title, description)

    @_retry_decorator
    async def _classify_ollama_impl(self, title: str, description: str) -> str | None:
        """Classify using Ollama native API (with retry)."""
        prompt = _build_classification_prompt(title, description)
        client = await self._get_client()

        try:
            response = await client.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 20,
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
            return None

        raw_output = data.get("response", "").strip()
        return _normalize_category(raw_output)

    async def _classify_lmstudio(self, title: str, description: str) -> str | None:
        """Classify using LM Studio OpenAI-compatible API."""
        return await self._classify_lmstudio_impl(title, description)

    @_retry_decorator
    async def _classify_lmstudio_impl(self, title: str, description: str) -> str | None:
        """Classify using LM Studio OpenAI-compatible API (with retry)."""
        prompt = _build_classification_prompt(title, description)
        client = await self._get_client()

        try:
            # LM Studio uses OpenAI-compatible chat completions API
            response = await client.post(
                f"{self._base_url}/v1/chat/completions",
                json={
                    "model": self._model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 20,
                },
            )
            response.raise_for_status()
            data = response.json()
        except asyncio.CancelledError:
            raise
        except httpx.TimeoutException as exc:
            raise ClassificationError(
                f"LM Studio classification timed out for '{title}': {exc}",
                retryable=True,
            ) from exc
        except httpx.RequestError as exc:
            raise ClassificationError(
                f"LM Studio connection failed for '{title}': {exc}",
                retryable=True,
            ) from exc
        except httpx.HTTPStatusError as exc:
            self._handle_http_error(exc, title, "LM Studio")
            return None

        # Parse OpenAI-compatible response
        choices = data.get("choices", [])
        if not choices:
            logger.warning(f"No choices in LM Studio response for '{title}'")
            return None

        message = choices[0].get("message", {})
        raw_output = message.get("content", "").strip()
        return _normalize_category(raw_output)

    def _handle_http_error(self, exc: httpx.HTTPStatusError, title: str, provider: str) -> None:
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
        elif status_code >= 500:
            raise ClassificationError(
                f"{provider} server error ({status_code}) for '{title}': {detail}",
                retryable=True,
            ) from exc
        else:
            raise ClassificationError(
                f"{provider} request failed ({status_code}) for '{title}': {detail}",
                retryable=False,
            ) from exc

    async def classify_batch(self, jobs: list[tuple[str, str]]) -> list[str | None]:
        """Classify multiple jobs concurrently with rate limiting.

        Args:
            jobs: List of (title, description) tuples

        Returns:
            List of category slugs (or None for failures), same order as input
        """
        if not jobs:
            return []

        semaphore = asyncio.Semaphore(self._max_concurrent)
        completed = 0
        lock = asyncio.Lock()

        async def classify_with_semaphore(
            idx: int, title: str, description: str
        ) -> tuple[int, str | None]:
            nonlocal completed
            async with semaphore:
                try:
                    result = await self.classify_job(title, description)
                except Exception as e:
                    logger.error(f"Error classifying job '{title}': {e}")
                    result = None

                async with lock:
                    completed += 1
                    if completed % 10 == 0:
                        logger.info(f"Classification progress: {completed}/{len(jobs)}")

                return (idx, result)

        tasks = [
            classify_with_semaphore(i, title, description)
            for i, (title, description) in enumerate(jobs)
        ]

        try:
            results_with_idx = await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.warning("Batch classification cancelled")
            raise

        results: list[str | None] = [None] * len(jobs)
        for idx, result in results_with_idx:
            results[idx] = result

        success_count = sum(1 for r in results if r is not None)
        logger.info(f"Batch classification complete: {success_count}/{len(jobs)} successful")

        return results

    async def classify_batch_with_progress(
        self,
        jobs: list[tuple[str, str]],
        progress_callback: Any | None = None,
    ) -> list[str | None]:
        """Classify multiple jobs with optional progress callback."""
        return await self.classify_batch(jobs)


# Singleton instance
_classifier_instance: JobClassifier | None = None


async def get_classifier() -> JobClassifier:
    """Get or create the job classifier instance."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = JobClassifier()
    return _classifier_instance


def reset_classifier() -> None:
    """Reset the classifier singleton (useful for testing)."""
    global _classifier_instance
    if _classifier_instance:
        asyncio.create_task(_classifier_instance.close())
    _classifier_instance = None
