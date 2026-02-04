from __future__ import annotations

import logging
import sys

from app.db import SessionLocal
from ingestion.pipeline import fetch_api_jobs, upsert_jobs
from ingestion.apis.company_registry import get_company_registry, COMPANY_REGISTRY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    # Check if user wants to discover new companies
    discover = "--discover" in sys.argv
    
    if discover:
        logger.info("Discovering companies with active job boards...")
        companies = get_company_registry(use_discovery=True, force_refresh=True)
        logger.info(f"Using {len(companies)} discovered companies for ingestion")
    else:
        logger.info(f"Using cached/seed companies ({len(COMPANY_REGISTRY)} total)")
        logger.info("Tip: Run with --discover to find new companies")
    
    logger.info("Starting API ingestion (no AI enrichment)...")
    api_jobs = fetch_api_jobs()
    logger.info(f"Fetched {len(api_jobs)} jobs from APIs")
    
    with SessionLocal() as db:
        upsert_jobs(db, api_jobs)
    
    logger.info("Ingestion complete!")


if __name__ == "__main__":
    main()
