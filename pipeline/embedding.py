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

from pipeline.config import get_settings
from pipeline.http_client import get_http_client
from pipeline.text import clean_text_for_embedding

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
        self._dimensions = self._settings.embedding_dimensions
        self._base_url = self._settings.ollama_base_url.rstrip("/")

    def _coerce_embedding_dimensions(self, embedding: list[float]) -> list[float]:
        if len(embedding) == self._dimensions:
            return embedding
        if len(embedding) > self._dimensions:
            return embedding[: self._dimensions]
        raise EmbeddingError(
            f"Embedding model returned {len(embedding)} dimensions, expected at least {self._dimensions}",
            retryable=False,
        )

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        text = clean_text_for_embedding(text)

        try:
            if self._provider == "lmstudio":
                return await self._embed_lmstudio(text)
            return await self._embed_ollama(text)
        except asyncio.CancelledError:
            logger.warning("Embedding request cancelled")
            raise

    async def embed_many(self, texts: Iterable[str], batch_size: int = 3) -> list[list[float]]:
        """Generate embeddings for multiple texts with provider-aware batching."""
        texts_list = [clean_text_for_embedding(text) for text in texts]
        if not texts_list:
            return []

        if self._provider == "lmstudio":
            return await self._embed_many_lmstudio(texts_list, batch_size=batch_size)

        results = []
        for i in range(0, len(texts_list), batch_size):
            batch = texts_list[i : i + batch_size]
            batch_results = await asyncio.gather(
                *[self._embed_ollama(t) for t in batch], return_exceptions=True
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
            if status_code >= 500:
                raise EmbeddingError(
                    f"Ollama server error. Status: {status_code}. "
                    f"Base URL: {self._base_url}. Response: {detail}",
                    retryable=True,
                ) from exc
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

        return self._coerce_embedding_dimensions(data["embedding"])

    async def _embed_lmstudio(self, text: str) -> list[float]:
        """Generate embedding using LM Studio OpenAI-compatible API."""
        try:
            return await self._embed_lmstudio_impl(text)
        except asyncio.CancelledError:
            raise

    def _parse_lmstudio_embeddings(self, data: dict, expected_count: int) -> list[list[float]]:
        items = data.get("data")
        if not isinstance(items, list) or len(items) != expected_count:
            raise EmbeddingError(
                f"LM Studio response returned {len(items) if isinstance(items, list) else 0} embeddings, "
                f"expected {expected_count}. Base URL: {self._base_url}. Response keys: {list(data.keys())}",
                retryable=False,
            )

        ordered: list[list[float] | None] = [None] * expected_count
        for position, item in enumerate(items):
            if not isinstance(item, dict) or "embedding" not in item:
                raise EmbeddingError(
                    f"LM Studio response missing embedding at position {position}. "
                    f"Base URL: {self._base_url}",
                    retryable=False,
                )

            raw_index = item.get("index", position)
            if not isinstance(raw_index, int) or raw_index < 0 or raw_index >= expected_count:
                raise EmbeddingError(
                    f"LM Studio response returned invalid embedding index {raw_index}. "
                    f"Base URL: {self._base_url}",
                    retryable=False,
                )
            ordered[raw_index] = self._coerce_embedding_dimensions(item["embedding"])

        missing = [index for index, embedding in enumerate(ordered) if embedding is None]
        if missing:
            raise EmbeddingError(
                f"LM Studio response missing embedding indexes {missing}. Base URL: {self._base_url}",
                retryable=False,
            )
        return [embedding for embedding in ordered if embedding is not None]

    def _handle_lmstudio_http_status(self, exc: httpx.HTTPStatusError) -> None:
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
        if status_code >= 500:
            raise EmbeddingError(
                f"LM Studio server error. Status: {status_code}. "
                f"Base URL: {self._base_url}. Response: {detail}",
                retryable=True,
            ) from exc
        raise EmbeddingError(
            f"LM Studio request failed. Status: {status_code}. "
            f"Base URL: {self._base_url}. Response: {detail}",
            retryable=False,
        ) from exc

    @_retry_decorator
    async def _embed_lmstudio_impl(self, text: str) -> list[float]:
        """Generate embedding using LM Studio OpenAI-compatible API (with retry)."""
        return (await self._embed_lmstudio_many_impl([text]))[0]

    async def _embed_many_lmstudio(self, texts: list[str], batch_size: int) -> list[list[float]]:
        results: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            try:
                results.extend(await self._embed_lmstudio_many_impl(batch))
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001  # batch retry: any embedding failure falls back to per-item
                logger.warning(
                    "LM Studio batch embedding failed for %d texts; retrying individually: %s",
                    len(batch),
                    exc,
                )
                for offset, text in enumerate(batch):
                    try:
                        results.append(await self._embed_lmstudio_impl(text))
                    except Exception as item_exc:  # noqa: BLE001  # wrap any per-item embedding failure as EmbeddingError
                        raise EmbeddingError(
                            f"Failed to embed text at index {i + offset}: {item_exc}",
                            retryable=_is_retryable_exception(item_exc),
                        ) from item_exc
        return results

    @_retry_decorator
    async def _embed_lmstudio_many_impl(self, texts: list[str]) -> list[list[float]]:
        """Generate one or more embeddings in a single OpenAI-compatible API request."""
        if not texts:
            return []

        client = get_http_client()
        try:
            response = await client.post(
                f"{self._base_url}/v1/embeddings",
                json={
                    "model": self._model,
                    "input": texts if len(texts) > 1 else texts[0],
                    "dimensions": self._dimensions,
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
            self._handle_lmstudio_http_status(exc)

        data = response.json()
        return self._parse_lmstudio_embeddings(data, len(texts))
