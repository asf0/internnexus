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
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.db import SessionLocal, engine
from app.models import Job
from app.services.embedding_service import EmbeddingService
from ingestion.enrichment import enrich_jobs
from ingestion.pipeline import fetch_api_jobs, upsert_jobs
from ingestion.apis.simplify_jobs_parser import get_category_context

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ============================================================================
# STEP 1: Discover Companies
# ============================================================================

async def verify_greenhouse_board(slug: str) -> bool:
    """Check if a company has a Greenhouse job board."""
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
                timeout=5.0
            )
            return response.status_code == 200
    except Exception:
        return False


async def verify_lever_board(slug: str) -> bool:
    """Check if a company has a Lever job board."""
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.lever.co/v0/postings/{slug}?mode=json",
                timeout=5.0
            )
            return response.status_code == 200
    except Exception:
        return False


async def verify_company(slug: str) -> bool:
    """Check if company has either Greenhouse or Lever board."""
    gh_result, lv_result = await asyncio.gather(
        verify_greenhouse_board(slug),
        verify_lever_board(slug)
    )
    return gh_result or lv_result


def discover_companies() -> list[str]:
    """Discover companies with active job boards."""
    logger.info("=" * 60)
    logger.info("STEP 1: Discovering companies with active job boards...")
    logger.info("=" * 60)
    
    # Import the registry to get known companies
    from ingestion.apis.company_registry import COMPANY_REGISTRY
    
    slugs = set(COMPANY_REGISTRY)
    
    # Add some additional common slugs to check
    additional_slugs = {
        "airbnb", "stripe", "netflix", "uber", "spotify", "slack",
        "figma", "notion", "discord", "zapier", "airtable", "canva",
        "amplitude", "brex", "datadog", "plaid", "shopify", "zendesk",
        "cloudflare", "twilio", "github", "gitlab", "mongodb", "elastic",
    }
    slugs.update(additional_slugs)
    
    logger.info(f"Verifying {len(slugs)} company slugs...")
    
    async def run_verification():
        semaphore = asyncio.Semaphore(5)
        
        async def verify_with_semaphore(slug: str) -> tuple[str, bool]:
            async with semaphore:
                result = await verify_company(slug)
                return slug, result
        
        tasks = [verify_with_semaphore(slug) for slug in slugs]
        return await asyncio.gather(*tasks)
    
    results = asyncio.run(run_verification())
    verified = [slug for slug, result in results if result]
    verified.sort()
    
    logger.info(f"Found {len(verified)} active job boards")
    return verified


# ============================================================================
# STEP 2: Fetch and Ingest Jobs
# ============================================================================

def fetch_and_ingest() -> int:
    """Fetch jobs from all sources and upsert to database."""
    logger.info("=" * 60)
    logger.info("STEP 2: Fetching and ingesting jobs...")
    logger.info("=" * 60)
    
    # Get job categories from SimplifyJobs markdown
    logger.info("Loading category context...")
    category_context = get_category_context()
    
    # Fetch from all API sources
    logger.info("Fetching from Greenhouse and Lever APIs...")
    api_jobs = fetch_api_jobs()
    logger.info(f"Fetched {len(api_jobs)} jobs from APIs")
    
    # Deduplicate within batch BEFORE enrichment (to avoid unnecessary embedding)
    from ingestion.pipeline import fingerprint_for
    seen_fingerprints = {}
    unique_jobs = []
    for job in api_jobs:
        fp = fingerprint_for(job)
        if fp not in seen_fingerprints:
            unique_jobs.append(job)
            seen_fingerprints[fp] = True
    
    if len(unique_jobs) < len(api_jobs):
        logger.info(f"Deduped {len(api_jobs) - len(unique_jobs)} jobs within batch ({len(unique_jobs)} unique)")
    api_jobs = unique_jobs
    
    # Enrich with visa/F1 info and categories (WITHOUT embedding - that happens after insert)
    logger.info("Enriching jobs with visa/F1 info and categories (no embedding yet)...")
    api_jobs = enrich_jobs(api_jobs, category_context, skip_embedding=True)
    
    # Upsert to database first (new jobs inserted without embeddings)
    logger.info("Upserting to database (new jobs will be added, existing updated)...")
    with SessionLocal() as db:
        upsert_jobs(db, api_jobs)
    
    # Now embed only jobs that don't have embeddings yet
    logger.info("Generating embeddings for jobs without them...")
    embedded_count, _ = generate_embeddings()
    
    logger.info(f"Ingestion complete: {len(api_jobs)} jobs processed, {embedded_count} newly embedded")
    return len(api_jobs)


# ============================================================================
# STEP 3: Cleanup Locations
# ============================================================================

# Import location cleanup logic
US_STATES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
    'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
    'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
    'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
    'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
    'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
    'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
    'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
    'DC': 'District of Columbia'
}

STATE_NAMES_TO_ABBR = {v.lower(): k for k, v in US_STATES.items()}
US_STATE_NAMES = set(v.lower() for v in US_STATES.values())

COUNTRY_ALIASES = {
    'usa': 'United States', 'us': 'United States', 'u.s.': 'United States',
    'united states': 'United States', 'united states of america': 'United States',
    'uk': 'United Kingdom', 'gb': 'United Kingdom', 'great britain': 'United Kingdom',
    'ca': 'Canada', 'canada': 'Canada', 'au': 'Australia', 'australia': 'Australia',
    'de': 'Germany', 'germany': 'Germany', 'fr': 'France', 'france': 'France',
    'remote': 'Remote',
}


def clean_location(location: str) -> dict:
    """Parse and normalize a location string."""
    if not location:
        return {"location": "", "city": None, "state": None, "country": None}
    
    original = location.strip()
    parts = [p.strip() for p in re.split(r'[,/]', original) if p.strip()]
    
    city, state, country = None, None, None
    
    for part in parts:
        part_lower = part.lower()
        
        # Check country
        if part_lower in COUNTRY_ALIASES:
            country = COUNTRY_ALIASES[part_lower]
            continue
        
        # Check US state abbreviation
        if part.upper() in US_STATES:
            state = part.upper()
            country = country or "United States"
            continue
        
        # Check US state full name
        if part_lower in US_STATE_NAMES:
            state = STATE_NAMES_TO_ABBR[part_lower]
            country = country or "United States"
            continue
        
        # Otherwise treat as city
        if not city and len(part) > 1:
            city = part.title()
    
    # Build normalized location
    loc_parts = []
    if city:
        loc_parts.append(city)
    if state:
        loc_parts.append(state)
    if country:
        loc_parts.append(country)
    
    normalized = ', '.join(loc_parts) if loc_parts else original
    
    return {"location": normalized, "city": city, "state": state, "country": country}


def cleanup_locations() -> int:
    """Normalize location data for all jobs."""
    logger.info("=" * 60)
    logger.info("STEP 3: Cleaning up locations...")
    logger.info("=" * 60)
    
    with Session(engine) as session:
        jobs = session.query(Job).filter(Job.is_active == True).all()
        logger.info(f"Found {len(jobs)} active jobs to process")
        
        updated = 0
        for job in jobs:
            if not job.location:
                continue
            
            result = clean_location(job.location)
            
            changed = (
                result["location"] != job.location or
                result["city"] != job.city or
                result["state"] != job.state or
                result["country"] != job.country
            )
            
            if changed:
                job.location = result["location"]
                job.city = result["city"]
                job.state = result["state"]
                job.country = result["country"]
                updated += 1
        
        session.commit()
        logger.info(f"Updated {updated} job locations")
        return updated


# ============================================================================
# STEP 4: Generate Embeddings
# ============================================================================

def clean_text(text: str) -> str:
    """Clean and truncate text for embedding.
    
    Uses higher limit for ASCII text (English) and lower limit for 
    non-ASCII text (Japanese, Chinese, etc.) which uses more tokens per char.
    """
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&[a-zA-Z]+;', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Check if text is mostly ASCII (a-z, 0-9, common punctuation)
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    is_mostly_ascii = len(text) == 0 or (ascii_chars / len(text)) > 0.8
    
    # Use appropriate limit based on character type
    max_chars = 6000 if is_mostly_ascii else 2000
    
    return text[:max_chars]


def generate_embeddings(batch_size: int = 50) -> tuple[int, int]:
    """Generate embeddings for jobs without them."""
    logger.info("=" * 60)
    logger.info("STEP 4: Generating embeddings...")
    logger.info("=" * 60)
    
    db = SessionLocal()
    
    jobs = db.query(Job).filter(Job.description_embedding == None).all()
    total = len(jobs)
    
    if total == 0:
        logger.info("All jobs already have embeddings!")
        db.close()
        return 0, 0
    
    logger.info(f"Found {total} jobs without embeddings")
    
    try:
        embedder = EmbeddingService()
        logger.info(f"Using embedding provider: {embedder._provider}")
    except Exception as e:
        logger.error(f"Failed to initialize embedding service: {e}")
        db.close()
        return 0, total
    
    success, errors = 0, 0
    
    for i, job in enumerate(jobs):
        try:
            text = clean_text(job.description_text)
            if not text or len(text) < 50:
                continue
            
            embedding = embedder.embed(text)
            job.description_embedding = embedding
            success += 1
            
            if (i + 1) % batch_size == 0:
                db.commit()
                logger.info(f"  [{i+1}/{total}] Committed batch ({success} success, {errors} errors)")
            
            if (i + 1) % 25 == 0:
                logger.info(f"  [{i+1}/{total}] {job.company} - {job.title[:40]}...")
                
        except Exception as e:
            errors += 1
            if errors <= 3:
                logger.warning(f"  [{i+1}/{total}] Error: {e}")
    
    db.commit()
    db.close()
    
    logger.info(f"Embedding complete: {success} success, {errors} errors")
    return success, errors


# ============================================================================
# Main Pipeline
# ============================================================================

def run_pipeline(skip_discover: bool = False) -> dict:
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
        companies = discover_companies()
        results["companies_verified"] = len(companies)
    
    # Step 2: Fetch and ingest jobs
    results["jobs_fetched"] = fetch_and_ingest()
    
    # Step 3: Cleanup locations
    results["locations_cleaned"] = cleanup_locations()
    
    # Step 4: Generate embeddings
    success, errors = generate_embeddings()
    results["embeddings_success"] = success
    results["embeddings_errors"] = errors
    
    elapsed = time.time() - start
    logger.info("=" * 60)
    logger.info(f"PIPELINE COMPLETE - {elapsed:.1f}s ({elapsed/60:.1f} min)")
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
        """
    )
    parser.add_argument(
        "--continuous", "-c",
        action="store_true",
        help="Run continuously"
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=3600,
        help="Interval in seconds (default: 3600 = 1 hour)"
    )
    parser.add_argument(
        "--step",
        choices=["discover", "ingest", "cleanup", "embed"],
        help="Run only a specific step"
    )
    parser.add_argument(
        "--skip-discover",
        action="store_true",
        help="Skip company discovery step (faster)"
    )
    
    args = parser.parse_args()
    
    def run_once():
        if args.step == "discover":
            discover_companies()
        elif args.step == "ingest":
            fetch_and_ingest()
        elif args.step == "cleanup":
            cleanup_locations()
        elif args.step == "embed":
            generate_embeddings()
        else:
            run_pipeline(skip_discover=args.skip_discover)
    
    if args.continuous:
        logger.info(f"Starting continuous pipeline (interval: {args.interval}s)")
        while True:
            try:
                run_once()
            except KeyboardInterrupt:
                logger.info("Interrupted, exiting...")
                break
            except Exception as e:
                logger.error(f"Pipeline error: {e}")
            
            logger.info(f"Sleeping for {args.interval}s...")
            time.sleep(args.interval)
    else:
        run_once()


if __name__ == "__main__":
    main()
