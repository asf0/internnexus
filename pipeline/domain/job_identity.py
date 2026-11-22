"""Stable job identity helpers."""

from __future__ import annotations

from internnexus_core.identity import fingerprint_for as _core_fingerprint_for

from pipeline.domain.schemas import JobSchema


def fingerprint_for(job: JobSchema) -> str:
    """Generate a stable fingerprint from a job's apply URL."""
    return _core_fingerprint_for(job.apply_url)
