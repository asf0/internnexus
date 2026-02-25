"""Job fetching module - fetch jobs from APIs, ingest into database."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.pipeline import fetch_api_jobs, upsert_jobs
from pipeline.repositories.sqlalchemy_repo import AsyncSessionLocal

logger = logging.getLogger(__name__)

ENABLE_SCRAPERS = False
ENABLE_LINKEDIN = False
ENABLE_INDEED = False


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
    api_jobs = await fetch_api_jobs(
        api_fetch_concurrency=api_fetch_concurrency,
        not_found_cooldown_hours=not_found_cooldown_hours,
        run_id=run_id,
    )
    logger.info(f"Fetched {len(api_jobs)} jobs from APIs")

    all_jobs = api_jobs

    logger.info("Upserting to database (new jobs will be added, existing updated)...")

    if session is None:
        async with AsyncSessionLocal() as db:
            await upsert_jobs(db, all_jobs)
    else:
        await upsert_jobs(session, all_jobs)

    logger.info(f"Ingestion complete: {len(all_jobs)} jobs processed")
    return len(all_jobs), batch_start_time
