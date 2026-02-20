"""Parse SimplifyJobs markdown files to extract job categories."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Dict

import httpx

from backend.app.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)


class SimplifyJobsCategoryParser:
    """Parse SimplifyJobs README files to extract job categories by company."""

    # Map of emoji/section headers to category names
    CATEGORY_MAP = {
        "💻": "software_engineering",
        "📱": "product_management",
        "🤖": "data_science_ai",
        "📈": "quantitative_finance",
        "🔧": "hardware_engineering",
    }

    async def parse_github_readme(self, url: str) -> Dict[str, str]:
        """Parse SimplifyJobs GitHub README to extract job categories.

        Args:
            url: GitHub raw content URL to markdown file

        Returns:
            Dict mapping company slugs/names to their categories
        """
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch {url}: {response.status_code}")
                    return {}

                return self._parse_markdown(response.text)
        except Exception as e:
            logger.error(f"Error parsing SimplifyJobs README: {e}")
            return {}

    def _parse_markdown(self, markdown: str) -> Dict[str, str]:
        """Parse markdown content to extract categories.

        Args:
            markdown: Raw markdown content from SimplifyJobs

        Returns:
            Dict mapping company names to categories
        """
        categories = {}
        current_category = None

        lines = markdown.split("\n")

        for line in lines:
            # Detect category headers (e.g., "## 💻 Software Engineering Internship Roles")
            for emoji, category_name in self.CATEGORY_MAP.items():
                if f"## {emoji}" in line or f"##**{emoji}" in line:
                    current_category = category_name
                    logger.debug(f"Found category: {current_category}")
                    break

            # Extract company names from table rows
            # Format: | <strong><a href="...">CompanyName</a></strong>
            if current_category and "|" in line and "<strong>" in line:
                company_match = re.search(r"<strong>(?:<a[^>]*>)?([^<]+)(?:</a>)?</strong>", line)
                if company_match:
                    company_name = company_match.group(1).strip()
                    if company_name and company_name not in ("Company", "Location", "Application"):
                        categories[company_name.lower()] = current_category

        logger.info(f"Extracted {len(categories)} company-category mappings from markdown")
        return categories

    async def get_all_categories(self) -> Dict[str, str]:
        """Fetch and parse both Summer 2026 and New Grad job categories.

        Returns:
            Combined dict of company -> category mappings
        """
        intern_url = settings.simplify_jobs_intern_url
        new_grad_url = settings.simplify_jobs_new_grad_url

        logger.info("Parsing SimplifyJobs category data...")

        # Parse both files concurrently
        intern_cats, grad_cats = await asyncio.gather(
            self.parse_github_readme(intern_url),
            self.parse_github_readme(new_grad_url),
            return_exceptions=True,
        )

        # Merge results
        all_categories = {}
        if isinstance(intern_cats, dict):
            all_categories.update(intern_cats)
        if isinstance(grad_cats, dict):
            all_categories.update(grad_cats)

        logger.info(f"Total company-category mappings: {len(all_categories)}")
        return all_categories


async def get_category_context_async() -> Dict[str, str]:
    """Get category context for enrichment (async version).

    Returns:
        Dict mapping company names to job categories
    """
    try:
        parser = SimplifyJobsCategoryParser()
        categories = await parser.get_all_categories()
        return categories
    except Exception as e:
        logger.error(f"Failed to get category context: {e}")
        return {}


def get_category_context() -> Dict[str, str]:
    """Get category context for enrichment.

    Returns:
        Dict mapping company names to job categories
    """
    try:
        parser = SimplifyJobsCategoryParser()
        categories = asyncio.run(parser.get_all_categories())
        return categories
    except Exception as e:
        logger.error(f"Failed to get category context: {e}")
        return {}
