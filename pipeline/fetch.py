"""Job fetching module - fetch jobs from APIs, ingest into database."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import AsyncSessionLocal
from pipeline.enrichment import enrich_jobs
from pipeline.pipeline import fetch_api_jobs, upsert_jobs, fingerprint_for
from pipeline.apis.simplify_jobs_parser import get_category_context_async

logger = logging.getLogger(__name__)

ENABLE_SCRAPERS = False
ENABLE_LINKEDIN = False
ENABLE_INDEED = False


async def fetch_and_ingest(session: AsyncSession | None = None) -> tuple[int, datetime]:
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

    logger.info("Loading category context...")
    category_context = await get_category_context_async()

    logger.info("Fetching from API sources (Greenhouse, Lever, Ashby)...")
    api_jobs = fetch_api_jobs()
    logger.info(f"Fetched {len(api_jobs)} jobs from APIs")

    all_jobs = api_jobs

    seen_fingerprints = {}
    unique_jobs = []
    for job in all_jobs:
        fp = fingerprint_for(job)
        if fp not in seen_fingerprints:
            unique_jobs.append(job)
            seen_fingerprints[fp] = True

    if len(unique_jobs) < len(all_jobs):
        logger.info(
            f"Deduped {len(all_jobs) - len(unique_jobs)} jobs within batch "
            f"({len(unique_jobs)} unique)"
        )
    all_jobs = unique_jobs

    logger.info("Enriching jobs (disabled - testing clean ATS data)...")
    all_jobs = await enrich_jobs(all_jobs, category_context, skip_embedding=True)

    logger.info("Upserting to database (new jobs will be added, existing updated)...")

    if session is None:
        async with AsyncSessionLocal() as db:
            await upsert_jobs(db, all_jobs)
    else:
        await upsert_jobs(session, all_jobs)

    logger.info(f"Ingestion complete: {len(all_jobs)} jobs processed")
    return len(all_jobs), batch_start_time
