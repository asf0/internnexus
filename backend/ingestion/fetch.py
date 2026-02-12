"""Job fetching module - fetch jobs from APIs and ingest into database."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from ingestion.enrichment import enrich_jobs
from ingestion.pipeline import fetch_api_jobs, async_upsert_jobs, fingerprint_for
from ingestion.apis.simplify_jobs_parser import get_category_context_async
from ingestion.embeddings import generate_embeddings

logger = logging.getLogger(__name__)


async def fetch_and_ingest(session: AsyncSession | None = None) -> int:
    """Fetch jobs from all sources and upsert to database.

    Args:
        session: Optional existing session. If None, creates a new session.

    Returns:
        Number of jobs fetched
    """
    logger.info("=" * 60)
    logger.info("STEP 2: Fetching and ingesting jobs...")
    logger.info("=" * 60)

    # Get job categories from SimplifyJobs markdown
    logger.info("Loading category context...")
    category_context = await get_category_context_async()

    # Fetch from all API sources
    logger.info("Fetching from Greenhouse and Lever APIs...")
    api_jobs = fetch_api_jobs()
    logger.info(f"Fetched {len(api_jobs)} jobs from APIs")

    # Deduplicate within batch BEFORE enrichment (to avoid unnecessary embedding)
    seen_fingerprints = {}
    unique_jobs = []
    for job in api_jobs:
        fp = fingerprint_for(job)
        if fp not in seen_fingerprints:
            unique_jobs.append(job)
            seen_fingerprints[fp] = True

    if len(unique_jobs) < len(api_jobs):
        logger.info(
            f"Deduped {len(api_jobs) - len(unique_jobs)} jobs within batch "
            f"({len(unique_jobs)} unique)"
        )
    api_jobs = unique_jobs

    # Enrich with visa/F1 info and categories (WITHOUT embedding - that happens after insert)
    logger.info("Enriching jobs with visa/F1 info and categories (no embedding yet)...")
    api_jobs = await enrich_jobs(api_jobs, category_context, skip_embedding=True)

    # Upsert to database first (new jobs inserted without embeddings)
    logger.info("Upserting to database (new jobs will be added, existing updated)...")

    if session is None:
        async with AsyncSessionLocal() as db:
            await async_upsert_jobs(db, api_jobs)
    else:
        await async_upsert_jobs(session, api_jobs)

    # Now embed only jobs that don't have embeddings yet
    logger.info("Generating embeddings for jobs without them...")
    embedded_count, _ = await generate_embeddings(session=session)

    logger.info(
        f"Ingestion complete: {len(api_jobs)} jobs processed, {embedded_count} newly embedded"
    )
    return len(api_jobs)
