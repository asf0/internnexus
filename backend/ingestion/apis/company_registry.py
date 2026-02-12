from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Set

import httpx

from app.config import get_settings
from ingestion.data import load_common_companies

logger = logging.getLogger(__name__)
settings = get_settings()

# Cache file for discovered companies
CACHE_FILE = Path(__file__).parent / "discovered_companies.json"

# Verified companies with active Greenhouse/Lever job boards
SEED_COMPANIES: list[str] = [
    "airbnb",
    "airtable",
    "amplitude",
    "brex",
    "cloudflare",
    "coinbase",
    "databricks",
    "datadog",
    "discord",
    "elastic",
    "figma",
    "gitlab",
    "okta",
    "plaid",
    "robinhood",
    "roblox",
    "stripe",
    "twilio",
]


async def harvest_companies_from_github() -> Set[str]:
    """Harvest companies from SimplifyJobs GitHub repos (Summer 2026 + New Grad)."""
    try:
        intern_url = settings.simplify_jobs_intern_url
        new_grad_url = settings.simplify_jobs_new_grad_url

        urls = [intern_url, new_grad_url]
        all_content = ""

        logger.info("Harvesting companies from SimplifyJobs GitHub repos...")

        async with httpx.AsyncClient(timeout=10.0) as client:
            for url in urls:
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        all_content += response.text
                        logger.debug(f"  ✓ Fetched {url}")
                    else:
                        logger.debug(f"  ✗ Failed {url} (Status: {response.status_code})")
                except Exception as e:
                    logger.debug(f"  ✗ Error fetching {url}: {e}")

        if not all_content:
            logger.warning("No content fetched from SimplifyJobs repos")
            return set()

        # Extract Lever and Greenhouse slugs from URLs
        import re

        lever_pattern = r"jobs\.lever\.co/([a-zA-Z0-9\-\_]+)"
        gh_pattern = r"boards\.greenhouse\.io/([a-zA-Z0-9\-\_]+)"

        lever_slugs = set(re.findall(lever_pattern, all_content))
        gh_slugs = set(re.findall(gh_pattern, all_content))

        # Clean up common false positives
        ignore_list = {
            "jobs",
            "apply",
            "careers",
            "engineering",
            "people",
            "team",
            "internal",
            "workhere",
        }
        all_slugs = (lever_slugs | gh_slugs) - ignore_list

        logger.info(f"Harvested {len(all_slugs)} unique companies from GitHub")
        return {s.lower() for s in all_slugs}
    except Exception as e:
        logger.warning(f"GitHub harvesting failed: {e}")
        return set()


async def verify_greenhouse_board(slug: str) -> bool:
    """Check if a company has a Greenhouse job board."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.greenhouse_api_url}/{slug}/jobs")
            return response.status_code == 200
    except Exception:
        return False


async def verify_lever_board(slug: str) -> bool:
    """Check if a company has a Lever job board."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.lever_api_url}/{slug}?mode=json")
            return response.status_code == 200
    except Exception:
        return False


async def verify_company(slug: str) -> bool:
    """Check if company has either Greenhouse or Lever board."""
    try:
        gh_result, lv_result = await asyncio.gather(
            verify_greenhouse_board(slug), verify_lever_board(slug), return_exceptions=True
        )
        return (gh_result is True) or (lv_result is True)
    except Exception:
        return False


async def discover_companies_async() -> list[str]:
    """Discover companies with active job boards asynchronously."""
    # Start with seed companies
    base_slugs = set(SEED_COMPANIES)

    # Add common companies
    base_slugs.update(load_common_companies())

    # Harvest from SimplifyJobs GitHub repos
    github_slugs = await harvest_companies_from_github()
    base_slugs.update(github_slugs)

    logger.info(f"Total candidates to verify: {len(base_slugs)}")

    semaphore = asyncio.Semaphore(10)  # Limit concurrent requests

    async def verify_with_semaphore(slug: str) -> tuple[str, bool]:
        async with semaphore:
            result = await verify_company(slug)
            if result:
                logger.info(f"✓ Found active board: {slug}")
            return slug, result

    tasks = [verify_with_semaphore(slug) for slug in base_slugs]
    results = await asyncio.gather(*tasks)

    verified = [slug for slug, result in results if result]
    verified.sort()

    logger.info(f"Discovered {len(verified)} active job boards")
    return verified


def load_cached_companies() -> list[str] | None:
    """Load companies from cache file."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE) as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            logger.warning(f"Could not load cache: {e}")
    return None


def save_cached_companies(companies: list[str]) -> None:
    """Save discovered companies to cache file."""
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(companies, f, indent=2)
        logger.info(f"Cached {len(companies)} companies to {CACHE_FILE}")
    except Exception as e:
        logger.warning(f"Could not save cache: {e}")


def get_company_registry(use_discovery: bool = True, force_refresh: bool = False) -> list[str]:
    """
    Get company registry with optional discovery.

    Args:
        use_discovery: If True, attempt to discover new companies.
                      Falls back to cache, then seed companies.
        force_refresh: If True, skip cache and force discovery.

    Returns:
        List of verified company slugs.
    """
    if not use_discovery:
        return SEED_COMPANIES

    # Try to load from cache first (unless force refresh)
    if not force_refresh:
        cached = load_cached_companies()
        if cached:
            logger.info(f"Using {len(cached)} cached companies")
            return cached

    # Try to discover new companies
    try:
        logger.info("Running company discovery...")
        discovered = asyncio.run(discover_companies_async())
        if discovered:
            save_cached_companies(discovered)
            return discovered
    except Exception as e:
        logger.warning(f"Company discovery failed: {e}")

    # Fall back to cache or seed companies
    cached = load_cached_companies()
    if cached:
        logger.info(f"Using cached companies as fallback ({len(cached)} companies)")
        return cached

    logger.info(f"Using seed companies as fallback ({len(SEED_COMPANIES)} companies)")
    return SEED_COMPANIES


# Export the registry - use discovery by default
COMPANY_REGISTRY: list[str] = get_company_registry(use_discovery=True)
