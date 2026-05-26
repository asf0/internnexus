"""Job fetching module - fetch jobs from APIs, ingest into database."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.ingest.core import fetch_api_jobs, upsert_jobs
from pipeline.repositories.sqlalchemy_repo import AsyncSessionLocal

logger = logging.getLogger(__name__)



async def fetch_and_ingest(
    session: AsyncSession | None = None,
    *,
    api_fetch_concurrency: int = 10,
    not_found_cooldown_hours: int = 24,
    run_id: str | None = None,
) -> tuple[int, datetime]:
    """Fetch jobs from all sources and upsert to database.

    Args:
        session: Optional existing session. If None, creates a new session.

    Returns:
        Tuple of (number of jobs fetched, batch start timestamp)
    """
    batch_start_time = datetime.now(timezone.utc)

    logger.info("=" * 60)
    logger.info("STEP 2: Fetching and ingesting jobs...")
    logger.info(f"Batch start time: {batch_start_time.isoformat()}")
    logger.info("=" * 60)

    logger.info("Fetching from API sources (Greenhouse, Lever, Ashby)...")
    greenhouse_jobs, lever_jobs, ashby_jobs = await fetch_api_jobs(
        api_fetch_concurrency=api_fetch_concurrency,
        not_found_cooldown_hours=not_found_cooldown_hours,
        run_id=run_id,
    )
    total_fetched = len(greenhouse_jobs) + len(lever_jobs) + len(ashby_jobs)
    logger.info(f"Fetched {total_fetched} jobs from APIs")

    logger.info("Upserting to database (new jobs will be added, existing updated)...")

    async def _upsert_all(db: AsyncSession) -> None:
        # Upsert and free each source list before starting the next so only one
        # source worth of JobSchema objects is alive during each upsert phase.
        nonlocal greenhouse_jobs, lever_jobs, ashby_jobs
        await upsert_jobs(db, greenhouse_jobs, deduplicate=False)
        del greenhouse_jobs
        await upsert_jobs(db, lever_jobs, deduplicate=False)
        del lever_jobs
        await upsert_jobs(db, ashby_jobs, deduplicate=False)
        del ashby_jobs

    if session is None:
        async with AsyncSessionLocal() as db:
            await _upsert_all(db)
    else:
        await _upsert_all(session)

    logger.info(f"Ingestion complete: {total_fetched} jobs processed")
    return total_fetched, batch_start_time
