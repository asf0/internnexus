"""Compatibility wrapper — embedding service now lives in internnexus-core.

The core service accepts explicit config parameters.  This wrapper resolves
service-local settings and delegates to the shared implementation.
"""

from __future__ import annotations

from internnexus_core.embedding import (
    OPENAI_COMPATIBLE_PROVIDER,
    EmbeddingConfig,
    EmbeddingError,
    RateLimitError,
    SettingsBoundQueryEmbeddingService,
    _is_retryable_exception,
)

from app.infra.config import get_settings

__all__ = [
    "EmbeddingConfig",
    "EmbeddingError",
    "OPENAI_COMPATIBLE_PROVIDER",
    "QueryEmbeddingService",
    "RateLimitError",
    "_is_retryable_exception",
]


class QueryEmbeddingService(SettingsBoundQueryEmbeddingService):
    """Backend-compatible wrapper resolving settings from the backend config."""

    def __init__(self, model: str | None = None) -> None:
        super().__init__(get_settings, model=model)
