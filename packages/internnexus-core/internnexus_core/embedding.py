"""Embedding service for OpenAI-compatible APIs."""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Iterable

import httpx

from internnexus_core.http_client import get_http_client
from internnexus_core.text import clean_text_for_embedding

logger = logging.getLogger(__name__)

OPENAI_COMPATIBLE_PROVIDER = "openai-compatible"


@dataclass(frozen=True)
class EmbeddingConfig:
    """Minimal configuration for the embedding service.

    Services resolve their own settings and pass this dataclass to the
    core service constructor.  Core never imports backend or pipeline config.
    """

    model: str = "qwen3-embedding-4b"
    dimensions: int = 1024
    base_url: str = "http://localhost:8080/v1"
    # Slow self-hosted endpoints can take minutes for a full api_batch_size
    # request; services raise this when their backing model needs longer.
    timeout_seconds: float = 60.0


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


class QueryEmbeddingService:
    """Async query/resume embedding service for runtime matching."""

    def __init__(
        self,
        config: EmbeddingConfig | None = None,
        model: str | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        random_value: Callable[[], float] = random.random,
    ) -> None:
        cfg = config or EmbeddingConfig()
        self._model = model or cfg.model
        self._dimensions = cfg.dimensions
        self._base_url = cfg.base_url.rstrip("/")
        self._timeout_seconds = cfg.timeout_seconds
        self._sleep = sleep
        self._random_value = random_value

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
            return await self._embed_openai_compatible(text)
        except asyncio.CancelledError:
            logger.warning("Embedding request cancelled")
            raise

    async def embed_many(self, texts: Iterable[str], batch_size: int = 3) -> list[list[float]]:
        """Generate embeddings for multiple texts using API batching."""
        texts_list = [clean_text_for_embedding(text) for text in texts]
        if not texts_list:
            return []

        return await self._embed_many_openai_compatible(texts_list, batch_size=batch_size)

    async def _embed_openai_compatible(self, text: str) -> list[float]:
        """Generate embedding using an OpenAI-compatible API."""
        return await self._embed_openai_compatible_impl(text)

    def _parse_openai_compatible_embeddings(self, data: dict, expected_count: int) -> list[list[float]]:
        items = data.get("data")
        if not isinstance(items, list) or len(items) != expected_count:
            raise EmbeddingError(
                f"OpenAI-compatible API response returned {len(items) if isinstance(items, list) else 0} embeddings, "
                f"expected {expected_count}. Base URL: {self._base_url}. Response keys: {list(data.keys())}",
                retryable=False,
            )

        ordered: list[list[float] | None] = [None] * expected_count
        for position, item in enumerate(items):
            if not isinstance(item, dict) or "embedding" not in item:
                raise EmbeddingError(
                    f"OpenAI-compatible API response missing embedding at position {position}. "
                    f"Base URL: {self._base_url}",
                    retryable=False,
                )

            raw_index = item.get("index", position)
            if not isinstance(raw_index, int) or raw_index < 0 or raw_index >= expected_count:
                raise EmbeddingError(
                    f"OpenAI-compatible API response returned invalid embedding index {raw_index}. "
                    f"Base URL: {self._base_url}",
                    retryable=False,
                )
            ordered[raw_index] = self._coerce_embedding_dimensions(item["embedding"])

        missing = [index for index, embedding in enumerate(ordered) if embedding is None]
        if missing:
            raise EmbeddingError(
                f"OpenAI-compatible API response missing embedding indexes {missing}. Base URL: {self._base_url}",
                retryable=False,
            )
        return [embedding for embedding in ordered if embedding is not None]

    def _handle_openai_compatible_http_status(self, exc: httpx.HTTPStatusError) -> None:
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
                f"OpenAI-compatible API rate limited. Base URL: {self._base_url}. Retry-After: {retry_after}",
                retry_after=retry_after,
            ) from exc
        if status_code >= 500:
            raise EmbeddingError(
                f"OpenAI-compatible API server error. Status: {status_code}. "
                f"Base URL: {self._base_url}. Response: {detail}",
                retryable=True,
            ) from exc
        raise EmbeddingError(
            f"OpenAI-compatible API request failed. Status: {status_code}. "
            f"Base URL: {self._base_url}. Response: {detail}",
            retryable=False,
        ) from exc

    async def _embed_openai_compatible_impl(self, text: str) -> list[float]:
        """Generate embedding using an OpenAI-compatible API (with retry)."""
        return (await self._embed_openai_compatible_many_impl([text]))[0]

    async def _embed_many_openai_compatible(self, texts: list[str], batch_size: int) -> list[list[float]]:
        results: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            try:
                results.extend(await self._embed_openai_compatible_many_impl(batch))
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001  # batch retry: any embedding failure falls back to per-item
                logger.warning(
                    "OpenAI-compatible API batch embedding failed for %d texts; retrying individually: %s",
                    len(batch),
                    exc,
                )
                for offset, text in enumerate(batch):
                    try:
                        results.append(await self._embed_openai_compatible_impl(text))
                    except Exception as item_exc:  # noqa: BLE001  # wrap any per-item embedding failure as EmbeddingError
                        raise EmbeddingError(
                            f"Failed to embed text at index {i + offset}: {item_exc}",
                            retryable=_is_retryable_exception(item_exc),
                        ) from item_exc
        return results

    async def _embed_openai_compatible_many_impl(self, texts: list[str]) -> list[list[float]]:
        for attempt in range(1, 4):
            try:
                return await self._embed_openai_compatible_many_once(texts)
            except asyncio.CancelledError:
                raise
            except BaseException as exc:
                if attempt >= 3 or not _is_retryable_exception(exc):
                    raise
                exponential = min(10.0, float(2 ** (attempt - 1)))
                provider_delay = max(0.0, float(getattr(exc, "retry_after", None) or 0.0))
                delay = max(exponential, provider_delay) + self._random_value() * 0.5
                logger.warning("Retrying embedding request after attempt %d in %.1fs: %s", attempt, delay, exc)
                await self._sleep(delay)
        raise RuntimeError("embedding retry loop completed unexpectedly")

    async def _embed_openai_compatible_many_once(self, texts: list[str]) -> list[list[float]]:
        """Generate one or more embeddings in a single OpenAI-compatible API request."""
        if not texts:
            return []

        client = get_http_client()
        try:
            response = await client.post(
                self._endpoint_url("embeddings"),
                json={
                    "model": self._model,
                    "input": texts if len(texts) > 1 else texts[0],
                    "dimensions": self._dimensions,
                },
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
        except asyncio.CancelledError:
            raise
        except httpx.TimeoutException as exc:
            raise EmbeddingError(
                f"OpenAI-compatible API request timed out. Base URL: {self._base_url}. Error: {exc}",
                retryable=True,
            ) from exc
        except httpx.RequestError as exc:
            raise EmbeddingError(
                f"OpenAI-compatible API connection failed. Base URL: {self._base_url}. Error: {exc}",
                retryable=True,
            ) from exc
        except httpx.HTTPStatusError as exc:
            self._handle_openai_compatible_http_status(exc)

        data = response.json()
        return self._parse_openai_compatible_embeddings(data, len(texts))

    def _endpoint_url(self, endpoint: str) -> str:
        """Join an endpoint to either an API root or an existing ``/v1`` base."""
        suffix = endpoint.lstrip("/")
        if self._base_url.endswith("/v1"):
            return f"{self._base_url}/{suffix}"
        return f"{self._base_url}/v1/{suffix}"


class SettingsBoundQueryEmbeddingService:
    """Service-facing wrapper that resolves config from a settings loader.

    Backend and pipeline subclass this with their own ``get_settings`` so the
    delegate surface (including the internal methods their tests patch) lives
    in exactly one place.
    """

    def __init__(self, settings_loader, model: str | None = None) -> None:
        settings = settings_loader()
        self._service = QueryEmbeddingService(
            config=EmbeddingConfig(
                model=settings.embedding_model,
                dimensions=settings.embedding_dimensions,
                base_url=settings.openai_base_url,
                timeout_seconds=settings.embedding_timeout_seconds,
            ),
            model=model,
        )

    # -- Delegate public API --

    async def embed(self, text: str) -> list[float]:
        return await self._service.embed(text)

    async def embed_many(self, texts, batch_size: int = 3) -> list[list[float]]:
        return await self._service.embed_many(texts, batch_size=batch_size)

    # -- Delegate internal methods for test compatibility --

    async def _embed_openai_compatible(self, text: str) -> list[float]:
        return await self._service._embed_openai_compatible(text)

    async def _embed_openai_compatible_impl(self, text: str) -> list[float]:
        return await self._service._embed_openai_compatible_impl(text)

    async def _embed_many_openai_compatible(self, texts: list[str], batch_size: int) -> list[list[float]]:
        return await self._service._embed_many_openai_compatible(texts, batch_size=batch_size)

    async def _embed_openai_compatible_many_impl(self, texts: list[str]) -> list[list[float]]:
        return await self._service._embed_openai_compatible_many_impl(texts)

    def _coerce_embedding_dimensions(self, embedding: list[float]) -> list[float]:
        return self._service._coerce_embedding_dimensions(embedding)

    def _parse_openai_compatible_embeddings(self, data: dict, expected_count: int) -> list[list[float]]:
        return self._service._parse_openai_compatible_embeddings(data, expected_count)

    def _handle_openai_compatible_http_status(self, exc) -> None:
        return self._service._handle_openai_compatible_http_status(exc)

    # -- Expose internal attributes for test compatibility --

    @property
    def _model(self) -> str:
        return self._service._model

    @property
    def _dimensions(self) -> int:
        return self._service._dimensions

    @property
    def _base_url(self) -> str:
        return self._service._base_url
