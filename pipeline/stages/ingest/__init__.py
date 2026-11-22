"""Ingestion and upsert workflow."""

from pipeline.domain.job_identity import fingerprint_for
from pipeline.domain.sync_result import IngestResult
from pipeline.stages.ingest.fetch_all import mark_stale_jobs_inactive
from pipeline.stages.ingest.fetch import fetch_and_ingest
from pipeline.stages.ingest.upsert import upsert_jobs

__all__ = [
    "fetch_and_ingest",
    "fingerprint_for",
    "IngestResult",
    "mark_stale_jobs_inactive",
    "upsert_jobs",
]
