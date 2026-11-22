"""Compatibility wrapper — embedding service now lives in internnexus-core.

The core service accepts explicit config parameters.  This wrapper resolves
service-local settings and delegates to the shared implementation.
"""

from __future__ import annotations

from internnexus_core.embedding import SettingsBoundQueryEmbeddingService

from pipeline.infra.settings import get_settings

__all__ = ["QueryEmbeddingService"]


class QueryEmbeddingService(SettingsBoundQueryEmbeddingService):
    """Pipeline-compatible wrapper resolving settings from the pipeline config."""

    def __init__(self, model: str | None = None) -> None:
        super().__init__(get_settings, model=model)
