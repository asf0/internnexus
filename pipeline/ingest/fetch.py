"""Job fetching module - fetch jobs from APIs, ingest into database."""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.ingest.core import fetch_and_ingest_streamed
from pipeline.ingest.result import IngestResult
from pipeline.db import AsyncSessionLocal
from pipeline.runtime.config import get_config

logger = logging.getLogger(__name__)


async def fetch_and_ingest(
    session: AsyncSession | None = None,
    *,
    api_fetch_concurrency: int | None = None,
    not_found_cooldown_hours: int | None = None,
    slug_chunk_size: int | None = None,
    upsert_batch_size: int | None = None,
    sync_id: UUID | None = None,
) -> IngestResult:
    """Fetch jobs from all sources and upsert to database in streamed chunks.

    Args:
        session: Optional existing session. If None, creates a new session.

    Returns:
        Persistable synchronization context for stale-job validation.
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

    sync_id = sync_id or uuid4()

    logger.info("=" * 60)
    logger.info("STEP 2: Fetching and ingesting jobs...")
    logger.info("Synchronization ID: %s", sync_id)
    logger.info("=" * 60)

    logger.info("Fetching from API sources (Greenhouse, Lever, Ashby)...")

    if session is None:
        async with AsyncSessionLocal() as db:
            result = await fetch_and_ingest_streamed(
                db,
                chunk_size=slug_chunk_size,
                upsert_batch_size=upsert_batch_size,
                api_fetch_concurrency=api_fetch_concurrency,
                not_found_cooldown_hours=not_found_cooldown_hours,
                sync_id=sync_id,
            )
    else:
        result = await fetch_and_ingest_streamed(
            session,
            chunk_size=slug_chunk_size,
            upsert_batch_size=upsert_batch_size,
            api_fetch_concurrency=api_fetch_concurrency,
            not_found_cooldown_hours=not_found_cooldown_hours,
            sync_id=sync_id,
        )

    logger.info("Ingestion complete: %d jobs processed", result.total_fetched)
    return result
