from __future__ import annotations

import logging

from .stealth_browser import StealthBrowser
from ..schemas import JobSchema

logger = logging.getLogger(__name__)


class IndeedScraper:
    def __init__(self, browser: StealthBrowser | None = None) -> None:
        self._browser = browser or StealthBrowser()

    async def scrape(self, search_urls: list[str]) -> list[JobSchema]:
        jobs: list[JobSchema] = []
        for url in search_urls:
            try:
                async with self._browser.session() as (_, __, page):
                    await page.goto(url, wait_until="domcontentloaded")
                    await self._browser.wait_human()
                    logger.info("Fetched Indeed search page: %s", url)
                    # Placeholder: parse rendered HTML to extract job detail URLs and fields.
            except Exception as exc:  # pragma: no cover - network errors
                logger.warning("Indeed scrape failed for %s: %s", url, exc)
        return jobs
