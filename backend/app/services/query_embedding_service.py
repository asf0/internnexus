"""Compatibility wrapper — embedding service now lives in internnexus-core.

The core service accepts explicit config parameters.  This wrapper resolves
service-local settings and delegates to the shared implementation.
"""

from __future__ import annotations

from internnexus_core.embedding import (
    EmbeddingConfig,
    EmbeddingError,
    QueryEmbeddingService as _CoreQueryEmbeddingService,
    RateLimitError,
    _is_retryable_exception,
)

from app.config import get_settings

__all__ = [
    "EmbeddingConfig",
    "EmbeddingError",
    "QueryEmbeddingService",
    "RateLimitError",
    "_is_retryable_exception",
]


class QueryEmbeddingService:
    """Backend-compatible wrapper around the core embedding service.

    Accepts the same constructor signature as the original service
    (optional *model* override) and resolves settings from the backend config.
    """

    def __init__(self, model: str | None = None) -> None:
        settings = get_settings()
        self._service = _CoreQueryEmbeddingService(
            config=EmbeddingConfig(
                provider=settings.embedding_provider,
                model=settings.embedding_model,
                dimensions=settings.embedding_dimensions,
                base_url=settings.ollama_base_url,
            ),
            model=model,
        )

    # -- Delegate public API --

    async def embed(self, text: str) -> list[float]:
        return await self._service.embed(text)

    async def embed_many(self, texts, batch_size: int = 3) -> list[list[float]]:
        return await self._service.embed_many(texts, batch_size=batch_size)

    # -- Delegate internal methods for test compatibility --

    async def _embed_ollama(self, text: str) -> list[float]:
        return await self._service._embed_ollama(text)

    async def _embed_ollama_impl(self, text: str) -> list[float]:
        return await self._service._embed_ollama_impl(text)

    async def _embed_lmstudio(self, text: str) -> list[float]:
        return await self._service._embed_lmstudio(text)

    async def _embed_lmstudio_impl(self, text: str) -> list[float]:
        return await self._service._embed_lmstudio_impl(text)

    async def _embed_many_lmstudio(self, texts: list[str], batch_size: int) -> list[list[float]]:
        return await self._service._embed_many_lmstudio(texts, batch_size=batch_size)

    async def _embed_lmstudio_many_impl(self, texts: list[str]) -> list[list[float]]:
        return await self._service._embed_lmstudio_many_impl(texts)

    def _coerce_embedding_dimensions(self, embedding: list[float]) -> list[float]:
        return self._service._coerce_embedding_dimensions(embedding)

    def _parse_lmstudio_embeddings(self, data: dict, expected_count: int) -> list[list[float]]:
        return self._service._parse_lmstudio_embeddings(data, expected_count)

    def _handle_lmstudio_http_status(self, exc) -> None:
        return self._service._handle_lmstudio_http_status(exc)

    # -- Expose internal attributes for test monkeypatching --

    @property
    def _provider(self) -> str:
        return self._service._provider

    @property
    def _model(self) -> str:
        return self._service._model

    @property
    def _dimensions(self) -> int:
        return self._service._dimensions

    @property
    def _base_url(self) -> str:
        return self._service._base_url
