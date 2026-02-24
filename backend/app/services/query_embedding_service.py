"""Embedding service for generating text embeddings using Ollama or LM Studio."""

from __future__ import annotations

import asyncio
import logging
from typing import Iterable

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings
from app.http_client.client import get_http_client
from app.utils.text import clean_text_for_embedding

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Base exception for embedding failures."""

    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class RateLimitError(EmbeddingError):
    """Rate limit exceeded - retryable."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message, retryable=True)
        self.retry_after = retry_after


def _is_retryable_exception(exc: BaseException) -> bool:
    """Determine if an exception is retryable."""
    if isinstance(exc, asyncio.CancelledError):
        return False
    if isinstance(exc, EmbeddingError):
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


class QueryEmbeddingService:
    """Async query/resume embedding service for runtime matching."""

    def __init__(self, model: str | None = None) -> None:
        self._settings = get_settings()
        self._provider = self._settings.embedding_provider
        self._model = model or self._settings.embedding_model
        self._base_url = self._settings.ollama_base_url.rstrip("/")

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        text = clean_text_for_embedding(text)

        try:
            if self._provider == "lmstudio":
                return await self._embed_lmstudio(text)
            else:
                return await self._embed_ollama(text)
        except asyncio.CancelledError:
            logger.warning("Embedding request cancelled")
            raise

    async def embed_many(self, texts: Iterable[str], batch_size: int = 3) -> list[list[float]]:
        """Generate embeddings for multiple texts with concurrent batching."""
        texts_list = list(texts)
        results = []

        for i in range(0, len(texts_list), batch_size):
            batch = texts_list[i : i + batch_size]
            batch_results = await asyncio.gather(
                *[self.embed(t) for t in batch], return_exceptions=True
            )

            for j, result in enumerate(batch_results):
                if isinstance(result, BaseException):
                    if isinstance(result, asyncio.CancelledError):
                        raise result
                    raise EmbeddingError(
                        f"Failed to embed text at index {i + j}: {result}",
                        retryable=_is_retryable_exception(result),
                    ) from result
                results.append(result)

        return results

    async def _embed_ollama(self, text: str) -> list[float]:
        """Generate embedding using native Ollama API."""
        try:
            return await self._embed_ollama_impl(text)
        except asyncio.CancelledError:
            raise

    @_retry_decorator
    async def _embed_ollama_impl(self, text: str) -> list[float]:
        """Generate embedding using native Ollama API (with retry)."""
        client = get_http_client()
        try:
            response = await client.post(
                f"{self._base_url}/api/embeddings",
                json={
                    "model": self._model,
                    "prompt": text,
                    "options": {"num_ctx": 16384},
                },
                timeout=60.0,
            )
            response.raise_for_status()
        except asyncio.CancelledError:
            raise
        except httpx.TimeoutException as exc:
            raise EmbeddingError(
                f"Ollama request timed out. Base URL: {self._base_url}. Error: {exc}",
                retryable=True,
            ) from exc
        except httpx.RequestError as exc:
            raise EmbeddingError(
                f"Ollama connection failed. Base URL: {self._base_url}. Error: {exc}",
                retryable=True,
            ) from exc
        except httpx.HTTPStatusError as exc:
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
                    f"Ollama rate limited. Base URL: {self._base_url}. Retry-After: {retry_after}",
                    retry_after=retry_after,
                ) from exc
            elif status_code >= 500:
                raise EmbeddingError(
                    f"Ollama server error. Status: {status_code}. "
                    f"Base URL: {self._base_url}. Response: {detail}",
                    retryable=True,
                ) from exc
            else:
                raise EmbeddingError(
                    f"Ollama request failed. Status: {status_code}. "
                    f"Base URL: {self._base_url}. Response: {detail}",
                    retryable=False,
                ) from exc

        data = response.json()
        if "embedding" not in data:
            raise EmbeddingError(
                f"Ollama response missing 'embedding'. "
                f"Base URL: {self._base_url}. Response keys: {list(data.keys())}",
                retryable=False,
            )

        return data["embedding"]

    async def _embed_lmstudio(self, text: str) -> list[float]:
        """Generate embedding using LM Studio OpenAI-compatible API."""
        try:
            return await self._embed_lmstudio_impl(text)
        except asyncio.CancelledError:
            raise

    @_retry_decorator
    async def _embed_lmstudio_impl(self, text: str) -> list[float]:
        """Generate embedding using LM Studio OpenAI-compatible API (with retry)."""
        client = get_http_client()
        try:
            response = await client.post(
                f"{self._base_url}/v1/embeddings",
                json={
                    "model": self._model,
                    "input": text,
                },
                timeout=60.0,
            )
            response.raise_for_status()
        except asyncio.CancelledError:
            raise
        except httpx.TimeoutException as exc:
            raise EmbeddingError(
                f"LM Studio request timed out. Base URL: {self._base_url}. Error: {exc}",
                retryable=True,
            ) from exc
        except httpx.RequestError as exc:
            raise EmbeddingError(
                f"LM Studio connection failed. Base URL: {self._base_url}. Error: {exc}",
                retryable=True,
            ) from exc
        except httpx.HTTPStatusError as exc:
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
                    f"LM Studio rate limited. Base URL: {self._base_url}. Retry-After: {retry_after}",
                    retry_after=retry_after,
                ) from exc
            elif status_code >= 500:
                raise EmbeddingError(
                    f"LM Studio server error. Status: {status_code}. "
                    f"Base URL: {self._base_url}. Response: {detail}",
                    retryable=True,
                ) from exc
            else:
                raise EmbeddingError(
                    f"LM Studio request failed. Status: {status_code}. "
                    f"Base URL: {self._base_url}. Response: {detail}",
                    retryable=False,
                ) from exc

        data = response.json()
        if "data" not in data or not data["data"] or "embedding" not in data["data"][0]:
            raise EmbeddingError(
                f"LM Studio response missing embedding data. "
                f"Base URL: {self._base_url}. Response keys: {list(data.keys())}",
                retryable=False,
            )

        return data["data"][0]["embedding"]
