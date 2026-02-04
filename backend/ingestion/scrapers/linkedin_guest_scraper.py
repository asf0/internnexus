from __future__ import annotations

import logging
from typing import Any

from .stealth_browser import StealthBrowser
from ..schemas import JobSchema

logger = logging.getLogger(__name__)


class LinkedInGuestScraper:
    def __init__(self, browser: StealthBrowser | None = None) -> None:
        self._browser = browser or StealthBrowser()

    async def fetch_job_ids(self, search_url: str) -> list[str]:
        async with self._browser.session() as (_, __, page):
            await page.goto(search_url, wait_until="domcontentloaded")
            await self._browser.wait_human()
            return []

    async def fetch_job_detail(self, job_url: str) -> JobSchema | None:
        async with self._browser.session() as (_, __, page):
            await page.goto(job_url, wait_until="domcontentloaded")
            await self._browser.wait_human()
            logger.info("Fetched LinkedIn job page: %s", job_url)
            return None

    async def scrape(self, search_urls: list[str]) -> list[JobSchema]:
        jobs: list[JobSchema] = []
        for url in search_urls:
            try:
                job_ids = await self.fetch_job_ids(url)
                for job_id in job_ids:
                    job_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
                    job_detail = await self.fetch_job_detail(job_url)
                    if job_detail:
                        jobs.append(job_detail)
            except Exception as exc:  # pragma: no cover - network errors
                logger.warning("LinkedIn scrape failed for %s: %s", url, exc)
        return jobs
