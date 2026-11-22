"""Canonical in-memory job-board snapshots for changed-only reconciliation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from pipeline.domain.schemas import JobSchema
from pipeline.domain.job_identity import fingerprint_for
from internnexus_core.text import clean_job_description, strip_control_chars


@dataclass(frozen=True, slots=True)
class BoardSnapshot:
    """Canonical state of one successfully fetched ATS board."""

    board_hash: str
    manifest: dict[str, str]
    jobs_by_fingerprint: dict[str, JobSchema]

    @property
    def job_count(self) -> int:
        return len(self.manifest)


def _clean_description(text: str) -> str:
    """Match the description cleaning performed immediately before persistence."""
    return clean_job_description(text)


def _canonical_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None

    # PostgreSQL stores timestamptz values as instants. Treat a rare naive source
    # value as UTC so equivalent aware and naive UTC representations hash alike.
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    value = value.astimezone(timezone.utc)
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonical_job_payload(job: JobSchema) -> dict[str, str | None]:
    """Return only cleaned source fields whose persisted changes are material.

    Derived location enrichment, classification, and embedding fields are
    intentionally excluded. They are owned by downstream pipeline steps rather
    than by an ATS board snapshot.
    """
    return {
        "apply_url": strip_control_chars(job.apply_url),
        "company": strip_control_chars(job.company),
        "description_text": _clean_description(job.description_text),
        "job_type": job.job_type,
        "location": strip_control_chars(job.location),
        "posted_at": _canonical_datetime(job.posted_at),
        "title": strip_control_chars(job.title),
        "work_mode": job.work_mode,
    }


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def job_content_hash(job: JobSchema) -> str:
    """Return a SHA-256 digest of a job's canonical persisted source fields."""
    return hashlib.sha256(canonical_json(canonical_job_payload(job))).hexdigest()


def build_board_snapshot(jobs: Iterable[JobSchema]) -> BoardSnapshot:
    """Build an order-independent board manifest, hash, and deduplicated jobs.

    Duplicate apply URLs normally contain identical data. If an upstream board
    unexpectedly returns conflicting duplicates, the lexicographically smallest
    canonical payload wins. This makes the result deterministic without relying
    on unstable response ordering.
    """
    selected: dict[str, tuple[bytes, str, JobSchema]] = {}
    for job in jobs:
        fingerprint = fingerprint_for(job)
        canonical = canonical_json(canonical_job_payload(job))
        content_hash = hashlib.sha256(canonical).hexdigest()
        candidate = (canonical, content_hash, job)
        current = selected.get(fingerprint)
        if current is None or canonical < current[0]:
            selected[fingerprint] = candidate

    manifest = {
        fingerprint: selected[fingerprint][1]
        for fingerprint in sorted(selected)
    }
    jobs_by_fingerprint = {
        fingerprint: selected[fingerprint][2]
        for fingerprint in sorted(selected)
    }
    board_hash = hashlib.sha256(canonical_json(manifest)).hexdigest()
    return BoardSnapshot(
        board_hash=board_hash,
        manifest=manifest,
        jobs_by_fingerprint=jobs_by_fingerprint,
    )
