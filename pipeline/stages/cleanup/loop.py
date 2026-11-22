"""Shared cleanup loop for production and test modes."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pipeline.stages.cleanup.metadata import _merge_location_results
from pipeline.stages.cleanup.location_parser import _parse_location_only
from pipeline.stages.cleanup.location.state_parser import normalize_state_name
from pipeline.repositories import JobRepository
from pipeline.infra.lru import LRUDict

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CleanupRecord:
    job_id: UUID
    source: str
    original_location: str
    city: str | None
    state: str | None
    country: str | None
    original_city: str | None
    original_state: str | None
    original_country: str | None
    fix_source: str

    @property
    def changed(self) -> bool:
        return (
            self.city != self.original_city
            or self.state != self.original_state
            or self.country != self.original_country
        )


@dataclass
class CleanupLoopStats:
    processed: int
    emitted: int
    unique_locations: int


async def run_cleanup_loop(
    *,
    repo: JobRepository,
    since: datetime | None,
    process_all: bool,
    chunk_size: int,
    location_cache: LRUDict[str, dict],
    emit: Callable[[list[CleanupRecord]], Awaitable[int]],
    prepare_unknown: Callable[[list[str]], Awaitable[None]],
    after_batch: Callable[[], None] | None = None,
    limit: int | None = None,
) -> CleanupLoopStats:
    total_processed = 0
    total_emitted = 0

    total_count = await repo.get_total_count(since=since, process_all=process_all)
    logger.info(f"Found {total_count} jobs to process")

    last_id = None
    while True:
        if limit and total_processed >= limit:
            break

        jobs = await repo.fetch_jobs_batch_keyset(
            since=since,
            process_all=process_all,
            last_id=last_id,
            limit=chunk_size,
        )
        if not jobs:
            break

        last_id = jobs[-1].id
        batch_records, processed = await _prepare_batch_records(jobs, location_cache, prepare_unknown, limit, total_processed)
        total_processed += processed

        if batch_records:
            total_emitted += await emit(batch_records)

        if after_batch is not None:
            after_batch()

        if total_processed % 5000 == 0:
            logger.info(f"Processed {total_processed}/{min(total_count, limit or total_count)} jobs...")

    return CleanupLoopStats(
        processed=total_processed,
        emitted=total_emitted,
        unique_locations=len(location_cache),
    )


async def _prepare_batch_records(jobs, location_cache, prepare_unknown, limit, processed_so_far: int) -> tuple[list[CleanupRecord], int]:
    unknown = sorted({job.location for job in jobs if job.location and job.location not in location_cache})
    if unknown:
        await prepare_unknown(unknown)
    records: list[CleanupRecord] = []
    processed = 0
    for job in jobs:
        if limit and processed_so_far + processed >= limit:
            break
        processed += 1
        record = _cleanup_record(job, location_cache)
        if record:
            records.append(record)
    return records, processed


def _cleanup_record(job, location_cache) -> CleanupRecord | None:
    location = job.location
    if not location:
        return None
    parsed = location_cache.get(location)
    if parsed is None:
        parsed = _parse_location_only(location)
        location_cache[location] = parsed
    if parsed.get("state"):
        parsed["state"] = normalize_state_name(parsed["state"])
    final, source = _merge_location_results(location, parsed)
    return CleanupRecord(job.id, str(job.source), location, final["city"], final["state"], final["country"], job.city, job.state, job.country, source)
