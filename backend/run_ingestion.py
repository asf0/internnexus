from __future__ import annotations

import asyncio
import logging

from app.db import SessionLocal
from ingestion.enrichment import enrich_jobs
from ingestion.pipeline import fetch_api_jobs, upsert_jobs
from ingestion.scrapers.indeed_scraper import IndeedScraper
from ingestion.scrapers.linkedin_guest_scraper import LinkedInGuestScraper
from ingestion.apis.simplify_jobs_parser import get_category_context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_scrapers(category_context: dict) -> None:
    linkedin = LinkedInGuestScraper()
    indeed = IndeedScraper()

    linkedin_jobs = enrich_jobs(await linkedin.scrape([]), category_context)
    indeed_jobs = enrich_jobs(await indeed.scrape([]), category_context)

    with SessionLocal() as db:
        upsert_jobs(db, linkedin_jobs + indeed_jobs)


def main() -> None:
    # Get job categories from SimplifyJobs markdown
    logger.info("Fetching job categories from SimplifyJobs...")
    category_context = get_category_context()
    
    api_jobs = fetch_api_jobs()
    api_jobs = enrich_jobs(api_jobs, category_context)
    with SessionLocal() as db:
        upsert_jobs(db, api_jobs)

    asyncio.run(run_scrapers(category_context))


if __name__ == "__main__":
    main()
