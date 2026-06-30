"""Ingestion and upsert workflow."""

from pipeline.ingest.core import (
    fetch_api_jobs,
    mark_stale_jobs_inactive,
)
from pipeline.ingest.fetch import fetch_and_ingest
from pipeline.ingest.identity import fingerprint_for
from pipeline.ingest.result import IngestResult
from pipeline.ingest.upsert import upsert_jobs

__all__ = [
    "fetch_and_ingest",
    "fetch_api_jobs",
    "fingerprint_for",
    "IngestResult",
    "mark_stale_jobs_inactive",
    "upsert_jobs",
]
