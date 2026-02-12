"""Company discovery module - find companies with active job boards."""

from __future__ import annotations

import asyncio
import logging

import httpx

from app.config import get_settings
from ingestion.apis.company_registry import COMPANY_REGISTRY

logger = logging.getLogger(__name__)


async def verify_greenhouse_board(slug: str) -> bool:
    """Check if a company has a Greenhouse job board."""
    settings = get_settings()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.greenhouse_api_url}/{slug}/jobs", timeout=5.0)
            return response.status_code == 200
    except Exception:
        return False


async def verify_lever_board(slug: str) -> bool:
    """Check if a company has a Lever job board."""
    settings = get_settings()
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


async def discover_companies() -> list[str]:
    """Discover companies with active job boards."""
    logger.info("=" * 60)
    logger.info("STEP 1: Discovering companies with active job boards...")
    logger.info("=" * 60)

    slugs = set(COMPANY_REGISTRY)

    # Add some additional common slugs to check
    additional_slugs = {
        "airbnb",
        "stripe",
        "netflix",
        "uber",
        "spotify",
        "slack",
        "figma",
        "notion",
        "discord",
        "zapier",
        "airtable",
        "canva",
        "amplitude",
        "brex",
        "datadog",
        "plaid",
        "shopify",
        "zendesk",
        "cloudflare",
        "twilio",
        "github",
        "gitlab",
        "mongodb",
        "elastic",
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

    results = await run_verification()
    verified = [slug for slug, result in results if result]
    verified.sort()

    logger.info(f"Found {len(verified)} active job boards")
    return verified
