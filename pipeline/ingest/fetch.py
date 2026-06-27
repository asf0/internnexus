"""Job fetching module - fetch jobs from APIs, ingest into database."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.ingest.core import fetch_and_ingest_streamed
from pipeline.repositories.sqlalchemy_repo import AsyncSessionLocal
from pipeline.runtime.config import get_config

logger = logging.getLogger(__name__)


async def fetch_and_ingest(
    session: AsyncSession | None = None,
    *,
    api_fetch_concurrency: int | None = None,
    not_found_cooldown_hours: int | None = None,
    slug_chunk_size: int | None = None,
    upsert_batch_size: int | None = None,
    run_id: str | None = None,
) -> tuple[int, datetime]:
    """Fetch jobs from all sources and upsert to database in streamed chunks.

    Args:
        session: Optional existing session. If None, creates a new session.

    Returns:
        Tuple of (number of jobs fetched, batch start timestamp)
    """
    config = get_config()
    if api_fetch_concurrency is None:
        api_fetch_concurrency = config.api.fetch_concurrency
    if not_found_cooldown_hours is None:
        not_found_cooldown_hours = config.api.slug_404_cooldown_hours
    if slug_chunk_size is None:
        slug_chunk_size = config.ingest.slug_chunk_size
    if upsert_batch_size is None:
        upsert_batch_size = config.ingest.upsert_batch_size

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
                chunk_size=slug_chunk_size,
                upsert_batch_size=upsert_batch_size,
                api_fetch_concurrency=api_fetch_concurrency,
                not_found_cooldown_hours=not_found_cooldown_hours,
                run_id=run_id,
            )
    else:
        total_fetched = await fetch_and_ingest_streamed(
            session,
            chunk_size=slug_chunk_size,
            upsert_batch_size=upsert_batch_size,
            api_fetch_concurrency=api_fetch_concurrency,
            not_found_cooldown_hours=not_found_cooldown_hours,
            run_id=run_id,
        )

    logger.info(f"Ingestion complete: {total_fetched} jobs processed")
    return total_fetched, batch_start_time
