"""Job ingestion pipeline package.

Exports are resolved lazily to avoid import-time side effects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pipeline.stages.cleanup import cleanup_locations
    from pipeline.stages.embeddings import generate_embeddings
    from pipeline.stages.ingest import fetch_and_ingest, upsert_jobs

__all__ = [
    "fetch_and_ingest",
    "cleanup_locations",
    "generate_embeddings",
    "upsert_jobs",
]


def __getattr__(name: str) -> Any:
    if name == "fetch_and_ingest":
        from pipeline.stages.ingest import fetch_and_ingest

        return fetch_and_ingest
    if name == "cleanup_locations":
        from pipeline.stages.cleanup import cleanup_locations

        return cleanup_locations
    if name == "generate_embeddings":
        from pipeline.stages.embeddings import generate_embeddings

        return generate_embeddings
    if name == "upsert_jobs":
        from pipeline.stages.ingest import upsert_jobs

        return upsert_jobs
    raise AttributeError(f"module 'pipeline' has no attribute {name!r}")
