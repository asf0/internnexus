"""Job ingestion pipeline package.

Exports are resolved lazily to avoid import-time side effects.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "fetch_and_ingest",
    "cleanup_locations",
    "generate_embeddings",
    "fetch_api_jobs",
    "upsert_jobs",
]


def __getattr__(name: str) -> Any:
    if name == "fetch_and_ingest":
        from pipeline.fetch import fetch_and_ingest

        return fetch_and_ingest
    if name == "cleanup_locations":
        from pipeline.cleanup import cleanup_locations

        return cleanup_locations
    if name == "generate_embeddings":
        from pipeline.embeddings import generate_embeddings

        return generate_embeddings
    if name == "fetch_api_jobs":
        from pipeline.pipeline import fetch_api_jobs

        return fetch_api_jobs
    if name == "upsert_jobs":
        from pipeline.pipeline import upsert_jobs

        return upsert_jobs
    raise AttributeError(f"module 'pipeline' has no attribute {name!r}")
