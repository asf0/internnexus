"""Indeed job scraper.

Scrapes Indeed job search results using Playwright for JavaScript rendering.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
from typing import Literal
from urllib.parse import quote_plus

from .stealth_browser import StealthBrowser
from ..schemas import JobSchema
from ..apis.utils import detect_job_type_from_title, detect_work_mode_from_text

logger = logging.getLogger(__name__)

INDEED_SEARCH_QUERIES = [
    "software engineer",
    "software developer",
    "full stack developer",
    "frontend developer",
    "backend developer",
    "data scientist",
    "data engineer",
    "devops engineer",
    "product manager",
    "machine learning engineer",
]

INDEED_LOCATIONS = [
    "United States",
    "Canada",
    "United Kingdom",
    "Germany",
    "Remote",
]

# Patterns to strip from Indeed location text
LOCATION_CLEANUP_PATTERNS = [
    r"\d+\s+(hours?|days?|weeks?|months?)\s+ago",
    r"Be among the first\s+\d+\s+applicants?",
    r"See who\s+\w+\s+has hired for this role",
    r"\d+\s+applicants?",
    r"Full[-\s]time",
    r"Part[-\s]time",
    r"Contract",
    r"Temporary",
    r"Internship",
]


def _extract_job_type_from_location(
    location: str,
) -> Literal["internship", "full_time", "part_time"] | None:
    if not location:
        return None
    location_lower = location.lower()
    if "internship" in location_lower:
        return "internship"
    if re.search(r"part[\s-]?time", location_lower):
        return "part_time"
    if re.search(r"full[\s-]?time", location_lower):
        return "full_time"
    return None


def _clean_location_text(location: str) -> str:
    """Clean Indeed location text by removing metadata patterns."""
    if not location:
        return location

    cleaned = location
    for pattern in LOCATION_CLEANUP_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    # Clean up extra whitespace and punctuation
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"[,\s]+$", "", cleaned)  # Remove trailing commas/spaces

    return cleaned


class IndeedScraper:
    INDEED_SEARCH_URL = "https://www.indeed.com/jobs"

    def __init__(self, browser: StealthBrowser | None = None) -> None:
        self._browser = browser or StealthBrowser(headless=True)

    def _build_search_url(self, query: str, location: str, start: int = 0) -> str:
        params = {
            "q": query,
            "l": location,
            "sort": "date",
            "start": str(start),
        }
        param_str = "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
        return f"{self.INDEED_SEARCH_URL}?{param_str}"

    async def _extract_job_cards(self, page, search_url: str) -> list[dict]:
        await page.goto(search_url, wait_until="domcontentloaded")
        await self._browser.wait_human(2.0, 4.0)
        jobs: list[dict] = []

        # Check if we're blocked
        title = await page.title()
        if "blocked" in title.lower() or "access denied" in title.lower():
            logger.warning(f"Indeed blocked the request: {title}")
            return jobs

        try:
            await page.wait_for_selector(
                ".job_seen_beacon, .jobsearch-ResultsList, [data-jk], .result", timeout=15000
            )
        except Exception:
            logger.debug("No job cards found on Indeed page")
            return jobs

        job_cards = await page.query_selector_all(
            ".job_seen_beacon, li[data-jk], .result, .jobCard"
        )
        for card in job_cards:
            try:
                job_data = await self._parse_job_card(card)
                if job_data:
                    jobs.append(job_data)
            except Exception as exc:
                logger.debug(f"Failed to parse job card: {exc}")
        return jobs
        job_cards = await page.query_selector_all(".job_seen_beacon, li[data-jk], .result")
        for card in job_cards:
            try:
                job_data = await self._parse_job_card(card)
                if job_data:
                    jobs.append(job_data)
            except Exception as exc:
                logger.debug(f"Failed to parse job card: {exc}")
        return jobs

    async def _parse_job_card(self, card) -> dict | None:
        job_id = await card.get_attribute("data-jk")
        if not job_id:
            id_el = await card.query_selector("[data-jk]")
            if id_el:
                job_id = await id_el.get_attribute("data-jk")
        if not job_id:
            return None
        title = ""
        title_el = await card.query_selector("h2.jobTitle, h2 a, .jobTitle, .title a")
        if title_el:
            title = await title_el.inner_text()
        company = ""
        company_el = await card.query_selector(".companyName, .company, [data-company-name]")
        if company_el:
            company = await company_el.inner_text()
        location = ""
        location_el = await card.query_selector(".companyLocation, .location, .recJobLoc")
        if location_el:
            location = await location_el.inner_text()
            location = _clean_location_text(location)
        description = ""
        desc_el = await card.query_selector(".job-snippet, .summary, .job-snippet-container")
        if desc_el:
            description = await desc_el.inner_html()
        return {
            "job_id": job_id,
            "title": title.strip(),
            "company": company.strip(),
            "location": location.strip(),
            "description": description.strip(),
        }

    async def _fetch_job_detail(self, page, job_id: str, base_data: dict) -> JobSchema | None:
        job_url = f"https://www.indeed.com/viewjob?jk={job_id}"
        try:
            await page.goto(job_url, wait_until="domcontentloaded")
            await self._browser.wait_human(1.5, 3.0)
            description = base_data.get("description", "")
            desc_el = await page.query_selector(
                "#jobDescriptionText, .jobsearch-jobDescriptionText"
            )
            if desc_el:
                description = await desc_el.inner_html()
            title = base_data.get("title", "")
            title_el = await page.query_selector(
                ".jobsearch-JobInfoHeader-title, h1.jobsearch-JobInfoHeader-title"
            )
            if title_el:
                title = await title_el.inner_text()
            company = base_data.get("company", "")
            company_el = await page.query_selector(
                "[data-company-name], .jobsearch-InlineCompanyRating-companyHeader a"
            )
            if company_el:
                company = await company_el.inner_text()
            location = base_data.get("location", "")
            raw_location = location
            location_el = await page.query_selector(
                ".jobsearch-JobInfoHeader-subtitle .jobsearch-JobInfoHeader-subtitleLocation, [data-testid='inlineHeader-companyLocation']"
            )
            if location_el:
                raw_location = await location_el.inner_text()
                location = _clean_location_text(raw_location)
            if not title or not company:
                return None
            job_type = _extract_job_type_from_location(raw_location) or detect_job_type_from_title(
                title
            )
            work_mode = detect_work_mode_from_text(title, location)
            return JobSchema(
                source="indeed_scrape",
                title=title.strip(),
                company=company.strip(),
                location=location.strip() or "Remote",
                apply_url=job_url,
                description_text=description.strip(),
                job_type=job_type,
                work_mode=work_mode,
            )
        except Exception as exc:
            logger.debug(f"Failed to fetch Indeed job {job_id}: {exc}")
            if base_data.get("title") and base_data.get("company"):
                raw_location = base_data.get("location", "")
                job_type = _extract_job_type_from_location(
                    raw_location
                ) or detect_job_type_from_title(base_data["title"])
                location = _clean_location_text(raw_location)
                work_mode = detect_work_mode_from_text(base_data["title"], location)
                return JobSchema(
                    source="indeed_scrape",
                    title=base_data["title"],
                    company=base_data["company"],
                    location=location or "Remote",
                    apply_url=f"https://www.indeed.com/viewjob?jk={job_id}",
                    description_text=base_data.get("description", ""),
                    job_type=job_type,
                    work_mode=work_mode,
                )
            return None

    async def scrape_search(self, query: str, location: str, max_jobs: int = 50) -> list[JobSchema]:
        jobs: list[JobSchema] = []
        async with self._browser.session() as (_, __, page):
            search_url = self._build_search_url(query, location)
            logger.info(f"Indeed search: {query} in {location}")
            job_cards = await self._extract_job_cards(page, search_url)
            logger.info(f"Found {len(job_cards)} job cards for '{query}' in {location}")
            for i, card_data in enumerate(job_cards[:max_jobs]):
                try:
                    job = await self._fetch_job_detail(page, card_data["job_id"], card_data)
                    if job:
                        jobs.append(job)
                    if i < len(job_cards) - 1:
                        await self._browser.wait_human(1.0, 2.5)
                except Exception as exc:
                    logger.warning(f"Error fetching Indeed job {card_data.get('job_id')}: {exc}")
        return jobs

    async def scrape(
        self, queries: list[str] | None = None, locations: list[str] | None = None
    ) -> list[JobSchema]:
        queries = queries or INDEED_SEARCH_QUERIES
        locations = locations or INDEED_LOCATIONS
        all_jobs: list[JobSchema] = []
        for query in queries:
            for location in locations:
                try:
                    jobs = await self.scrape_search(query, location)
                    all_jobs.extend(jobs)
                    await asyncio.sleep(random.uniform(3.0, 6.0))
                except Exception as exc:
                    logger.warning(f"Indeed scrape failed for '{query}' in {location}: {exc}")
        logger.info(f"Indeed scrape complete: {len(all_jobs)} jobs")
        return all_jobs


async def scrape_indeed(
    queries: list[str] | None = None, locations: list[str] | None = None
) -> list[JobSchema]:
    scraper = IndeedScraper()
    return await scraper.scrape(queries, locations)
