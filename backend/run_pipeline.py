#!/usr/bin/env python3
"""
Complete job pipeline: discover companies, fetch jobs, cleanup, and embed.

This script runs the full pipeline:
1. Discover companies - Find companies with active Greenhouse/Lever boards
2. Fetch & ingest jobs - Fetch from all sources, deduplicate, upsert to DB
3. Cleanup locations - Normalize city/state/country fields
4. Generate embeddings - Create vector embeddings for job matching

Run modes:
  - Full pipeline: python run_pipeline.py
  - Continuous:    python run_pipeline.py --continuous --interval 3600
  - Single step:   python run_pipeline.py --step discover|ingest|cleanup|embed

Examples:
  python run_pipeline.py                      # Run full pipeline once
  python run_pipeline.py --step ingest        # Only fetch new jobs
  python run_pipeline.py --step embed         # Only generate embeddings
  python run_pipeline.py -c -i 1800           # Run every 30 minutes
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from ingestion.discovery import discover_companies
from ingestion.fetch import fetch_and_ingest
from ingestion.cleanup import cleanup_locations
from ingestion.embeddings import generate_embeddings
#from ingestion.reclassify import reclassify_visa

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def run_pipeline(skip_discover: bool = False) -> dict:
    """Run the complete pipeline."""
    start = time.time()
    logger.info("=" * 60)
    logger.info(f"PIPELINE START - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    results = {
        "companies_verified": 0,
        "jobs_fetched": 0,
        "locations_cleaned": 0,
        "embeddings_success": 0,
        "embeddings_errors": 0,
    }

    # Step 1: Discover companies (optional, slower)
    if not skip_discover:
        companies = await discover_companies()
        results["companies_verified"] = len(companies)

    # Step 2: Fetch and ingest jobs
    results["jobs_fetched"] = await fetch_and_ingest()

    # Step 3: Cleanup locations
    results["locations_cleaned"] = await cleanup_locations()

    # Step 4: Generate embeddings
    success, errors = await generate_embeddings()
    results["embeddings_success"] = success
    results["embeddings_errors"] = errors

    elapsed = time.time() - start
    logger.info("=" * 60)
    logger.info(f"PIPELINE COMPLETE - {elapsed:.1f}s ({elapsed / 60:.1f} min)")
    logger.info(f"  Companies verified: {results['companies_verified']}")
    logger.info(f"  Jobs fetched: {results['jobs_fetched']}")
    logger.info(f"  Locations cleaned: {results['locations_cleaned']}")
    logger.info(f"  Embeddings generated: {results['embeddings_success']}")
    logger.info(f"  Embedding errors: {results['embeddings_errors']}")
    logger.info("=" * 60)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run job ingestion pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_pipeline.py                      # Run full pipeline
  python run_pipeline.py --step ingest        # Only fetch new jobs  
  python run_pipeline.py --step embed         # Only generate embeddings
  python run_pipeline.py -c -i 1800           # Run every 30 minutes
  python run_pipeline.py --skip-discover      # Skip company discovery (faster)
        """,
    )
    parser.add_argument("--continuous", "-c", action="store_true", help="Run continuously")
    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=3600,
        help="Interval in seconds (default: 3600 = 1 hour)",
    )
    parser.add_argument(
        "--step",
        choices=["discover", "ingest", "cleanup", "embed", "reclassify"],
        help="Run only a specific step",
    )
    parser.add_argument(
        "--skip-discover", action="store_true", help="Skip company discovery step (faster)"
    )
    # parser.add_argument(
    #     "--reclassify-all", action="store_true", help="Reclassify all jobs (not just null values)"
    # )

    args = parser.parse_args()

    async def run_once():
        if args.step == "discover":
            await discover_companies()
        elif args.step == "ingest":
            await fetch_and_ingest()
        elif args.step == "cleanup":
            await cleanup_locations()
        elif args.step == "embed":
            await generate_embeddings()
        # elif args.step == "reclassify":
        #     await reclassify_visa(only_null=not args.reclassify_all, parallel=1)
        else:
            await run_pipeline(skip_discover=args.skip_discover)

    if args.continuous:
        logger.info(f"Starting continuous pipeline (interval: {args.interval}s)")
        while True:
            try:
                asyncio.run(run_once())
            except KeyboardInterrupt:
                logger.info("Interrupted, exiting...")
                break
            except Exception as e:
                logger.error(f"Pipeline error: {e}")

            logger.info(f"Sleeping for {args.interval}s...")
            time.sleep(args.interval)
    else:
        asyncio.run(run_once())


if __name__ == "__main__":
    main()
