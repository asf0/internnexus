"""Company discovery module - find companies with active job boards."""

from __future__ import annotations

import asyncio
import logging

from backend.app.config import get_settings
from backend.app.http_client.client import get_http_client

logger = logging.getLogger(__name__)


async def verify_greenhouse_board(slug: str) -> bool:
    """Check if a company has a Greenhouse job board."""
    settings = get_settings()
    try:
        client = get_http_client()
        response = await client.get(f"{settings.greenhouse_api_url}/{slug}/jobs", timeout=5.0)
        return response.status_code == 200
    except Exception:
        return False


async def verify_lever_board(slug: str) -> bool:
    """Check if a company has a Lever job board."""
    settings = get_settings()
    try:
        client = get_http_client()
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


async def discover_companies(slugs: set[str] | None = None) -> list[str]:
    """Discover companies with active job boards.

    Args:
        slugs: Optional set of company slugs to verify. If None, uses default set.
    """
    logger.info("=" * 60)
    logger.info("STEP 1: Discovering companies with active job boards...")
    logger.info("=" * 60)

    if slugs is None:
        from pipeline.apis.company_registry import SEED_COMPANIES
        from pipeline.data import load_common_companies

        slugs = set(SEED_COMPANIES)
        slugs.update(load_common_companies())

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
