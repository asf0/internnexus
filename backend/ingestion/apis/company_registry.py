from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Set

import httpx

from app.config import get_settings
from ingestion.data import load_common_companies

logger = logging.getLogger(__name__)
settings = get_settings()

CACHE_FILE = Path(__file__).parent / "discovered_companies.json"
CROSS_REFERENCE_FILE = Path(__file__).parent / "cross_reference_slugs.json"

ATS_PATTERNS = {
    "greenhouse": r"boards\.greenhouse\.io/([a-zA-Z0-9\-_]+)",
    "lever": r"jobs\.lever\.co/([a-zA-Z0-9\-_]+)",
    "ashby": r"jobs\.ashbyhq\.com/([a-zA-Z0-9\-_]+)",
    "workday": r"myworkdayjobs\.com/([a-zA-Z0-9\-_/]+)",
    "smartrecruiters": r"jobs\.smartrecruiters\.com/([a-zA-Z0-9\-_]+)",
}

IGNORE_SLUGS = {
    "jobs",
    "apply",
    "careers",
    "engineering",
    "people",
    "team",
    "internal",
    "workhere",
    "search",
    "results",
    "view",
    "job",
}


def extract_ats_slug_from_url(apply_url: str) -> tuple[str, str] | None:
    """Extract ATS platform and company slug from an apply URL.

    Args:
        apply_url: The job application URL

    Returns:
        Tuple of (ats_platform, slug) or None if not recognized
    """
    if not apply_url:
        return None
    for ats_platform, pattern in ATS_PATTERNS.items():
        match = re.search(pattern, apply_url, re.IGNORECASE)
        if match:
            slug = match.group(1).lower()
            slug = slug.rstrip("/-")
            if slug in IGNORE_SLUGS:
                continue
            if ats_platform == "workday":
                parts = slug.split("/")
                if parts:
                    slug = parts[0]
            return (ats_platform, slug)
    return None


def extract_slugs_from_jobs(jobs: list) -> dict[str, set[str]]:
    """Extract ATS slugs from a list of jobs with apply URLs.

    Args:
        jobs: List of JobSchema objects

    Returns:
        Dict mapping ATS platform to set of discovered slugs
    """
    discovered: dict[str, set[str]] = {
        "greenhouse": set(),
        "lever": set(),
        "ashby": set(),
        "workday": set(),
        "smartrecruiters": set(),
    }
    for job in jobs:
        url = getattr(job, "apply_url", None) or getattr(job, "apply_url", "")
        if not url:
            continue
        result = extract_ats_slug_from_url(url)
        if result:
            ats_platform, slug = result
            if ats_platform in discovered:
                discovered[ats_platform].add(slug)
    return discovered


def save_cross_reference_slugs(slugs: dict[str, set[str]]) -> None:
    """Save cross-referenced slugs to cache file."""
    try:
        data = {k: sorted(list(v)) for k, v in slugs.items() if v}
        with open(CROSS_REFERENCE_FILE, "w") as f:
            json.dump(data, f, indent=2)
        total = sum(len(v) for v in slugs.values())
        logger.info(f"Saved {total} cross-referenced slugs to {CROSS_REFERENCE_FILE}")
    except Exception as e:
        logger.warning(f"Could not save cross-reference slugs: {e}")


def load_cross_reference_slugs() -> dict[str, set[str]]:
    """Load cross-referenced slugs from cache file."""
    result: dict[str, set[str]] = {
        "greenhouse": set(),
        "lever": set(),
        "ashby": set(),
        "workday": set(),
        "smartrecruiters": set(),
    }
    if CROSS_REFERENCE_FILE.exists():
        try:
            with open(CROSS_REFERENCE_FILE) as f:
                data = json.load(f)
                for k, v in data.items():
                    if k in result and isinstance(v, list):
                        result[k] = set(v)
        except Exception as e:
            logger.warning(f"Could not load cross-reference slugs: {e}")
    return result


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

        lever_pattern = r"jobs\.lever\.co/([a-zA-Z0-9\-_]+)"
        gh_pattern = r"boards\.greenhouse\.io/([a-zA-Z0-9\-_]+)"
        ashby_pattern = r"jobs\.ashbyhq\.com/([a-zA-Z0-9\-_]+)"
        workday_pattern = r"myworkdayjobs\.com/([a-zA-Z0-9\-_/]+)"
        sr_pattern = r"jobs\.smartrecruiters\.com/([a-zA-Z0-9\-_]+)"

        lever_slugs = set(re.findall(lever_pattern, all_content))
        gh_slugs = set(re.findall(gh_pattern, all_content))
        ashby_slugs = set(re.findall(ashby_pattern, all_content))
        workday_slugs = set(re.findall(workday_pattern, all_content))
        sr_slugs = set(re.findall(sr_pattern, all_content))

        all_slugs = (lever_slugs | gh_slugs | ashby_slugs | workday_slugs | sr_slugs) - IGNORE_SLUGS

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
