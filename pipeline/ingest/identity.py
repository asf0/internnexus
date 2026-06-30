"""Stable job identity helpers."""

from __future__ import annotations

import uuid

from pipeline.domain import JobSchema


def fingerprint_for(job: JobSchema) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, job.apply_url))
