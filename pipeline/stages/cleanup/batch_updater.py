"""Batch processing with database for cleanup module."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.stages.cleanup.exporter import _process_test_mode_chunked
from pipeline.stages.cleanup.loop import CleanupRecord, run_cleanup_loop
from pipeline.stages.cleanup.normalizer import _normalize_existing_states
from pipeline.stages.cleanup.location_parser import _parse_location_only
from pipeline.repositories import LocationUpdate
from pipeline.infra.db import AsyncSessionLocal
from pipeline.repositories.sqlalchemy_repo import SQLAlchemyJobRepository
from pipeline.infra.lru import LRUDict

logger = logging.getLogger(__name__)


async def _apply_batch_updates(repo: SQLAlchemyJobRepository, updates: list[dict]) -> None:
    if not updates:
        return

    location_updates = [
        LocationUpdate(
            job_id=update["id"],
            city=update["city"],
            state=update["state"],
            country=update["country"],
            is_remote=False,
        )
        for update in updates
    ]
    await repo.update_job_locations(location_updates)


async def _process_production_mode_chunked(
    session: AsyncSession,
    since,
    process_all,
    limit: int | None,
    parse_concurrency: int = 12,
    chunk_size: int = 5000,
    location_cache_max_size: int = 10_000,
    warm_batch: int = 500,
) -> int:
    repo = SQLAlchemyJobRepository(session)
    location_cache: LRUDict[str, dict] = LRUDict(max_size=location_cache_max_size)

    logger.info("Building unique location cache and applying changes...")

    async def _warm(locations: list[str]) -> None:
        if not locations:
            return
        semaphore = asyncio.Semaphore(max(1, parse_concurrency))

        async def _parse_one(location: str) -> tuple[str, dict]:
            async with semaphore:
                return location, _parse_location_only(location)

        for i in range(0, len(locations), warm_batch):
            batch = locations[i : i + warm_batch]
            parsed_pairs = await asyncio.gather(*[_parse_one(loc) for loc in batch])
            for loc, parsed in parsed_pairs:
                location_cache[loc] = parsed

    async def emit(records: list[CleanupRecord]) -> int:
        changed = [r for r in records if r.changed]
        updates = [{"id": r.job_id, "city": r.city, "state": r.state, "country": r.country} for r in changed]
        if updates:
            await _apply_batch_updates(repo, updates)
        return len(changed)

    stats = await run_cleanup_loop(
        repo=repo,
        since=since,
        process_all=process_all,
        chunk_size=chunk_size,
        location_cache=location_cache,
        emit=emit,
        prepare_unknown=_warm,
        after_batch=session.expunge_all,
        limit=limit,
    )
    logger.info(f"Normalized {stats.unique_locations} unique locations")
    logger.info(f"Processed {stats.processed} jobs, updated {stats.emitted}")
    return stats.emitted


async def cleanup_locations(
    session: AsyncSession | None = None,
    since: datetime | None = None,
    process_all: bool = False,
    test_mode: bool = False,
    limit: int | None = None,
    parse_concurrency: int = 12,
    chunk_size: int = 5000,
    location_cache_max_size: int = 10_000,
    warm_batch: int = 500,
    normalize_since: datetime | None = None,
) -> int:
    logger.info("=" * 60)
    logger.info("STEP 3: Cleaning up locations...")
    logger.info("=" * 60)

    if test_mode:
        logger.info("TEST MODE: Writing results to CSV (no database changes)")

    should_close_session = session is None
    active_session = session if session is not None else AsyncSessionLocal()

    try:
        # The raw normalization UPDATEs otherwise scan every job row; scope
        # them to rows seen since the last completed run unless the caller
        # explicitly asked for a full pass (since/process_all semantics for
        # the parse loop below are unchanged).
        raw_update_since = since if since is not None else normalize_since
        if process_all:
            raw_update_since = since
        states_fixed = await _normalize_existing_states(active_session, since=raw_update_since)
        if states_fixed > 0:
            logger.info(f"Fixed {states_fixed} states that were actually countries")

        if since:
            logger.info(f"Processing jobs updated since {since}")
        elif process_all:
            logger.info("Processing ALL active jobs with locations")
        else:
            logger.info("Processing jobs that have not been normalized yet")

        if test_mode:
            return await _process_test_mode_chunked(
                active_session,
                since,
                process_all,
                limit,
                chunk_size=chunk_size,
                location_cache_max_size=location_cache_max_size,
            )

        return await _process_production_mode_chunked(
            active_session,
            since,
            process_all,
            limit,
            parse_concurrency=parse_concurrency,
            chunk_size=chunk_size,
            location_cache_max_size=location_cache_max_size,
            warm_batch=warm_batch,
        )
    finally:
        if should_close_session:
            await active_session.close()


async def delete_inactive_jobs(
    session: AsyncSession | None = None,
    sync_id: UUID | None = None,
    batch_size: int | None = None,
    max_attempts: int | None = None,
    base_delay: float | None = None,
    max_delay: float | None = None,
) -> int:
    logger.info("=" * 60)
    logger.info("STEP: Deleting inactive jobs (sync model)...")
    logger.info("=" * 60)

    should_close_session = session is None
    active_session = session if session is not None else AsyncSessionLocal()

    try:
        if sync_id is None:
            raise ValueError("sync_id is required to delete inactive jobs safely")
        repo = SQLAlchemyJobRepository(active_session)
        deleted_count = await repo.delete_inactive_jobs(
            sync_id,
            batch_size=batch_size,
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
        )
        if deleted_count == 0:
            logger.info("No inactive jobs to delete")
            return 0

        logger.info(f"Successfully deleted {deleted_count} inactive jobs")
        return deleted_count

    finally:
        if should_close_session:
            await active_session.close()
