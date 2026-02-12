#!/usr/bin/env python3
"""
Script to discover companies from job boards and verify they have Greenhouse/Lever boards.

Usage:
    python discover_companies.py          # Use default scrapers
    python discover_companies.py --add    # Verify and add to registry
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Set

import httpx

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import get_settings
from ingestion.data import load_common_companies

settings = get_settings()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def verify_greenhouse_board(slug: str) -> bool:
    """Check if a company has a Greenhouse job board."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.greenhouse_api_url}/{slug}/jobs", timeout=5.0)
            return response.status_code == 200
    except Exception:
        return False


async def verify_lever_board(slug: str) -> bool:
    """Check if a company has a Lever job board."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.lever_api_url}/{slug}?mode=json", timeout=5.0)
            return response.status_code == 200
    except Exception:
        return False


async def verify_company(slug: str) -> bool:
    """Check if company has either Greenhouse or Lever board."""
    gh_result, lv_result = await asyncio.gather(
        verify_greenhouse_board(slug), verify_lever_board(slug)
    )
    return gh_result or lv_result


async def discover_companies(count: int = 100) -> list[str]:
    """Discover companies with active job boards."""
    slugs = load_common_companies()

    logger.info(f"Verifying {len(slugs)} company slugs...")

    # Verify all companies concurrently with rate limiting
    verified = []
    semaphore = asyncio.Semaphore(5)  # Limit concurrent requests

    async def verify_with_semaphore(slug: str) -> tuple[str, bool]:
        async with semaphore:
            result = await verify_company(slug)
            if result:
                logger.info(f"✓ {slug}")
            return slug, result

    tasks = [verify_with_semaphore(slug) for slug in slugs]
    results = await asyncio.gather(*tasks)

    verified = [slug for slug, result in results if result]
    verified.sort()

    logger.info(f"\nFound {len(verified)} active job boards:")
    for slug in verified:
        print(f"  {slug}")

    return verified


async def main():
    import sys

    companies = await discover_companies()

    if "--add" in sys.argv and companies:
        # Generate Python code to update registry
        print("\n" + "=" * 60)
        print("Add these to company_registry.py:")
        print("=" * 60)
        code = "SEED_COMPANIES: list[str] = [\n"
        for company in companies:
            code += f'    "{company}",\n'
        code += "]\n"
        print(code)


if __name__ == "__main__":
    asyncio.run(main())
