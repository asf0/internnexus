"""Job fetching module - fetch jobs from APIs, ingest into database."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.ingest.core import fetch_and_ingest_streamed
from pipeline.repositories.sqlalchemy_repo import AsyncSessionLocal

logger = logging.getLogger(__name__)



async def fetch_and_ingest(
    session: AsyncSession | None = None,
    *,
    api_fetch_concurrency: int = 10,
    not_found_cooldown_hours: int = 24,
    run_id: str | None = None,
) -> tuple[int, datetime]:
    """Fetch jobs from all sources and upsert to database in streamed chunks.

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

    if session is None:
        async with AsyncSessionLocal() as db:
            total_fetched = await fetch_and_ingest_streamed(
                db,
                api_fetch_concurrency=api_fetch_concurrency,
                not_found_cooldown_hours=not_found_cooldown_hours,
                run_id=run_id,
            )
    else:
        total_fetched = await fetch_and_ingest_streamed(
            session,
            api_fetch_concurrency=api_fetch_concurrency,
            not_found_cooldown_hours=not_found_cooldown_hours,
            run_id=run_id,
        )

    logger.info(f"Ingestion complete: {total_fetched} jobs processed")
    return total_fetched, batch_start_time
