"""Job fetching module - fetch jobs from APIs and scrapers, ingest into database."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from ingestion.enrichment import enrich_jobs
from ingestion.pipeline import fetch_api_jobs, upsert_jobs, fingerprint_for
from ingestion.apis.simplify_jobs_parser import get_category_context_async
from ingestion.apis.company_registry import extract_slugs_from_jobs, save_cross_reference_slugs
from ingestion.embeddings import generate_embeddings

logger = logging.getLogger(__name__)

ENABLE_SCRAPERS = True
ENABLE_LINKEDIN = True
ENABLE_INDEED = False  # Indeed has strong anti-bot protection, disabled by default


async def fetch_scraped_jobs() -> list:
    """Fetch jobs from scrapers (LinkedIn, Indeed).

    Returns:
        List of JobSchema objects from scrapers
    """
    if not ENABLE_SCRAPERS:
        return []

    jobs = []

    if ENABLE_LINKEDIN:
        try:
            from ingestion.scrapers.linkedin_guest_scraper import scrape_linkedin

            logger.info("Scraping LinkedIn (guest mode)...")
            linkedin_jobs = await scrape_linkedin()
            logger.info(f"LinkedIn: {len(linkedin_jobs)} jobs")
            jobs.extend(linkedin_jobs)
        except Exception as exc:
            logger.warning(f"LinkedIn scraping failed: {exc}")

    if ENABLE_INDEED:
        try:
            from ingestion.scrapers.indeed_scraper import scrape_indeed

            logger.info("Scraping Indeed...")
            indeed_jobs = await scrape_indeed()
            logger.info(f"Indeed: {len(indeed_jobs)} jobs")
            jobs.extend(indeed_jobs)
        except Exception as exc:
            logger.warning(f"Indeed scraping failed: {exc}")

    return jobs


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

    logger.info("Fetching from API sources (Greenhouse, Lever, Workday, Ashby, SmartRecruiters)...")
    api_jobs = fetch_api_jobs()
    logger.info(f"Fetched {len(api_jobs)} jobs from APIs")

    scraped_jobs = await fetch_scraped_jobs()
    logger.info(f"Fetched {len(scraped_jobs)} jobs from scrapers")

    all_jobs = api_jobs + scraped_jobs

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

    if scraped_jobs:
        logger.info("Extracting ATS slugs from scraped jobs for cross-reference discovery...")
        try:
            discovered_slugs = extract_slugs_from_jobs(scraped_jobs)
            save_cross_reference_slugs(discovered_slugs)
        except Exception as exc:
            logger.warning(f"Cross-reference extraction failed: {exc}")

    logger.info("Enriching jobs with visa/F1 info and categories (no embedding yet)...")
    all_jobs = await enrich_jobs(all_jobs, category_context, skip_embedding=True)

    logger.info("Upserting to database (new jobs will be added, existing updated)...")

    if session is None:
        async with AsyncSessionLocal() as db:
            await upsert_jobs(db, all_jobs)
    else:
        await upsert_jobs(session, all_jobs)

    logger.info("Generating embeddings for jobs without them...")
    embedded_count, _ = await generate_embeddings(session=session)

    logger.info(
        f"Ingestion complete: {len(all_jobs)} jobs processed, {embedded_count} newly embedded"
    )
    return len(all_jobs), batch_start_time
