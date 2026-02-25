"""Batch processing with database for cleanup module."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.cleanup.exporter import _process_test_mode_chunked
from pipeline.cleanup.metadata import (
    _fetch_jobs_chunk,
    _get_metadata_result,
    _merge_location_results,
)
from pipeline.cleanup.normalizer import _normalize_existing_states
from pipeline.cleanup.parser import _parse_location_only
from pipeline.location.simple_parser import normalize_state_name
from pipeline.repositories import LocationUpdate
from pipeline.repositories.sqlalchemy_repo import AsyncSessionLocal, SQLAlchemyJobRepository

logger = logging.getLogger(__name__)


async def _get_total_count(repo: SQLAlchemyJobRepository, since, process_all) -> int:
    return await repo.get_total_count(since=since, process_all=process_all)


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
) -> int:
    from uuid import UUID

    repo = SQLAlchemyJobRepository(session)
    unique_locations: dict[str, dict] = {}
    total_processed = 0
    total_updated = 0
    changed_job_ids: list[UUID] = []

    total_count = await _get_total_count(repo, since, process_all)
    logger.info(f"Found {total_count} jobs to process")

    logger.info("Building unique location cache and applying changes...")

    async def _warm_location_cache(locations: list[str]) -> None:
        if not locations:
            return

        semaphore = asyncio.Semaphore(max(1, parse_concurrency))

        async def _parse_one(location: str) -> tuple[str, dict]:
            async with semaphore:
                return location, await _parse_location_only(location)

        parsed_pairs = await asyncio.gather(*[_parse_one(location) for location in locations])
        for location, parsed in parsed_pairs:
            unique_locations[location] = parsed

    last_id = None
    while True:
        if limit and total_processed >= limit:
            break

        rows, ashby_map, greenhouse_map, lever_map = await _fetch_jobs_chunk(
            repo, since, process_all, last_id, chunk_size
        )
        if not rows:
            break

        last_id = rows[-1]["id"]
        batch_updates = []

        unknown_locations = sorted(
            {
                row["location"]
                for row in rows
                if row["location"] and row["location"] not in unique_locations
            }
        )
        if unknown_locations:
            await _warm_location_cache(unknown_locations)
            if len(unique_locations) % 500 == 0:
                logger.info(f"Normalized {len(unique_locations)} unique locations...")

        for row in rows:
            if limit and total_processed >= limit:
                break

            total_processed += 1
            location = row["location"]

            if not location:
                continue

            parsed_result = unique_locations[location]

            if parsed_result.get("state"):
                parsed_result["state"] = normalize_state_name(parsed_result["state"])

            metadata_result, metadata_source = _get_metadata_result(
                row, ashby_map, greenhouse_map, lever_map
            )

            final_result, source_used = _merge_location_results(
                location, parsed_result, metadata_result, metadata_source
            )

            changed = (
                final_result["city"] != row["city"]
                or final_result["state"] != row["state"]
                or final_result["country"] != row["country"]
            )

            if changed:
                batch_updates.append(
                    {
                        "id": row["id"],
                        "city": final_result["city"],
                        "state": final_result["state"],
                        "country": final_result["country"],
                    }
                )

        if batch_updates:
            await _apply_batch_updates(repo, batch_updates)
            changed_job_ids.extend(update["id"] for update in batch_updates)
            total_updated += len(batch_updates)

        if total_processed % 5000 == 0:
            logger.info(
                f"Processed {total_processed}/{min(total_count, limit or total_count)} jobs..."
            )

    logger.info(f"Normalized {len(unique_locations)} unique locations")
    logger.info(f"Processed {total_processed} jobs, updated {total_updated}")

    if changed_job_ids:
        logger.info("Refreshing search vectors for cleanup-updated jobs...")
        refreshed_count = await repo.refresh_search_vectors_for_job_ids(changed_job_ids)
        logger.info(f"Refreshed search vectors for {refreshed_count} jobs")

    return total_updated


async def cleanup_locations(
    session: AsyncSession | None = None,
    since: datetime | None = None,
    process_all: bool = False,
    test_mode: bool = False,
    limit: int | None = None,
    parse_concurrency: int = 12,
    chunk_size: int = 5000,
) -> int:
    logger.info("=" * 60)
    logger.info("STEP 3: Cleaning up locations...")
    logger.info("=" * 60)

    if test_mode:
        logger.info("TEST MODE: Writing results to CSV (no database changes)")

    should_close_session = session is None
    if should_close_session:
        session = AsyncSessionLocal()

    try:
        states_fixed = await _normalize_existing_states(session)
        if states_fixed > 0:
            logger.info(f"Fixed {states_fixed} states that were actually countries")

        if since:
            logger.info(f"Processing jobs updated since {since}")
        elif process_all:
            logger.info("Processing ALL active jobs with locations")
        else:
            logger.info("Processing jobs that have not been normalized yet")

        if test_mode:
            return await _process_test_mode_chunked(session, since, process_all, limit)

        return await _process_production_mode_chunked(
            session,
            since,
            process_all,
            limit,
            parse_concurrency=parse_concurrency,
            chunk_size=chunk_size,
        )
    finally:
        if should_close_session:
            await session.close()


async def delete_inactive_jobs(session: AsyncSession | None = None) -> int:
    logger.info("=" * 60)
    logger.info("STEP: Deleting inactive jobs (sync model)...")
    logger.info("=" * 60)

    should_close_session = session is None
    if should_close_session:
        session = AsyncSessionLocal()

    try:
        repo = SQLAlchemyJobRepository(session)
        deleted_count = await repo.delete_inactive_jobs()
        if deleted_count == 0:
            logger.info("No inactive jobs to delete")
            return 0

        logger.info(f"Successfully deleted {deleted_count} inactive jobs")
        return deleted_count

    finally:
        if should_close_session:
            await session.close()
