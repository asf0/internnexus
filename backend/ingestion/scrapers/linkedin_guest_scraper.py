"""LinkedIn guest mode job scraper.

Scrapes LinkedIn job search results without requiring login.
Guest mode shows ~25 jobs per search query.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
from urllib.parse import quote_plus

from .stealth_browser import StealthBrowser
from ..schemas import JobSchema

logger = logging.getLogger(__name__)

LINKEDIN_SEARCH_QUERIES = [
    "software engineer",
    "software developer",
    "full stack developer",
    "frontend engineer",
    "backend engineer",
    "data scientist",
    "data engineer",
    "machine learning engineer",
    "devops engineer",
    "site reliability engineer",
    "security engineer",
    "product manager",
    "product owner",
    "engineering manager",
    "technical program manager",
    "internship",
]

LINKEDIN_LOCATIONS = [
    "United States",
    "Utah",
    "Tennesse",
    "Brazil",
    "Sao Paulo",
    "Korea",
    "Seoul",
    "Ireland",
    "Canada",
    "United Kingdom",
    "Germany",
    "Remote",
]

# Patterns to strip from LinkedIn location text
LOCATION_CLEANUP_PATTERNS = [
    r"\d+\s+(hours?|days?|weeks?|months?)\s+ago",
    r"Be among the first\s+\d+\s+applicants?",
    r"See who\s+\w+\s+has hired for this role",
    r"\d+\s+applicants?",
]


def _clean_location_text(location: str) -> str:
    """Clean LinkedIn location text by removing metadata patterns."""
    if not location:
        return location

    cleaned = location
    for pattern in LOCATION_CLEANUP_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    # Clean up extra whitespace and punctuation
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"[,\s]+$", "", cleaned)  # Remove trailing commas/spaces

    return cleaned


def _clean_description_text(description: str) -> str:
    """Remove 'Show more/Show less' button from end of LinkedIn description."""
    if not description:
        return description

    pattern = r"\s*<button[^>]*show-more-less-html__button[^>]*>.*?</button>\s*$"
    cleaned = re.sub(pattern, "", description, flags=re.IGNORECASE | re.DOTALL)

    cleaned = re.sub(r"\s*</(?:section|div)>\s*$", "", cleaned, flags=re.IGNORECASE)

    return cleaned.strip()


def _split_into_chunks(items: list, num_chunks: int) -> list[list]:
    """Split a list into roughly equal chunks."""
    chunk_size = max(1, len(items) // num_chunks)
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def _combine_results(results: list) -> list[JobSchema]:
    """Combine results from multiple workers, filtering out exceptions."""
    all_jobs = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Worker failed: {result}")
            continue
        all_jobs.extend(result)
    return all_jobs


class LinkedInGuestScraper:
    LINKEDIN_SEARCH_URL = "https://www.linkedin.com/jobs/search"
    LINKEDIN_JOB_URL = "https://www.linkedin.com/jobs/view"

    def __init__(self, browser: StealthBrowser | None = None) -> None:
        self._browser = browser or StealthBrowser(headless=True)

    def _build_search_url(self, query: str, location: str, start: int = 0) -> str:
        params = {
            "keywords": query,
            "location": location,
            "f_TPR": "r604800",
            "start": str(start),
        }
        param_str = "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
        return f"{self.LINKEDIN_SEARCH_URL}?{param_str}"

    async def _extract_job_ids(self, page, search_url: str) -> list[str]:
        await page.goto(search_url, wait_until="domcontentloaded")
        await self._browser.wait_human(2.0, 4.0)
        job_ids: list[str] = []
        try:
            await page.wait_for_selector(".job-search-card, .base-search-card", timeout=10000)
        except Exception:
            logger.debug("No job listings found on page")
            return job_ids

        cards = await page.query_selector_all(".job-search-card, .base-search-card")
        for card in cards:
            entity_urn = await card.get_attribute("data-entity-urn")
            if entity_urn and "jobPosting:" in entity_urn:
                job_id = entity_urn.split("jobPosting:")[-1]
                if job_id:
                    job_ids.append(job_id)
                    continue

            link = await card.query_selector("a[href*='/jobs/view/']")
            if link:
                href = await link.get_attribute("href")
                if href:
                    match = re.search(r"/jobs/view/[^/]+-(\d+)", href)
                    if match:
                        job_ids.append(match.group(1))

        return list(set(job_ids))

    async def _fetch_job_detail(self, page, job_id: str) -> JobSchema | None:
        job_url = f"{self.LINKEDIN_JOB_URL}/{job_id}/"
        try:
            await page.goto(job_url, wait_until="domcontentloaded")
            await self._browser.wait_human(1.5, 3.0)

            title = ""
            title_el = await page.query_selector(
                "h1.top-card-layout__title, h1.job-details-jobs-unified-top-card__job-title, .topcard__title"
            )
            if title_el:
                title = await title_el.inner_text()

            company = ""
            company_el = await page.query_selector(
                ".top-card-layout__first-subline a, .job-details-jobs-unified-top-card__company-name a, .topcard__org-name-link"
            )
            if company_el:
                company = await company_el.inner_text()
            else:
                company_el = await page.query_selector(
                    ".top-card-layout__first-subline, .job-details-jobs-unified-top-card__company-name, .topcard__flavor--black-link"
                )
                if company_el:
                    company = await company_el.inner_text()
                    if "·" in company:
                        company = company.split("·")[0].strip()

            location = ""
            location_el = await page.query_selector(
                ".top-card-layout__second-subline, .job-details-jobs-unified-top-card__primary-description-container span, .topcard__flavor--bullet"
            )
            if location_el:
                location = await location_el.inner_text()
                location = location.split("·")[0].strip() if "·" in location else location.strip()
                location = _clean_location_text(location)

            description = ""
            desc_el = await page.query_selector(
                ".show-more-less-html__markup, .jobs-description-content, .description__text"
            )
            if desc_el:
                description = await desc_el.inner_html()
                description = _clean_description_text(description)

            if not title or not company:
                logger.debug(f"Skipping job {job_id}: missing title or company")
                return None

            # Determine apply URL: external ATS link if available, otherwise LinkedIn
            apply_url = job_url
            easy_apply_btn = await page.query_selector(
                'button[data-control-name="jobdetails_topcard_inapply"], a[data-control-name="jobdetails_topcard_inapply"]'
            )
            if not easy_apply_btn:
                # Not Easy Apply - try to extract external apply URL
                external_btn = await page.query_selector(
                    'button[data-control-name="jobdetails_topcard_external_apply"], a[data-control-name="jobdetails_topcard_external_apply"]'
                )
                if external_btn:
                    href = await external_btn.get_attribute("href")
                    if href:
                        apply_url = href

            return JobSchema(
                source="linkedin_scrape",
                title=title.strip(),
                company=company.strip(),
                location=location.strip() or "Remote",
                apply_url=apply_url,
                description_text=description.strip(),
            )
        except Exception as exc:
            logger.debug(f"Failed to fetch job {job_id}: {exc}")
            return None

    async def _scrape_search_with_page(
        self, page, query: str, location: str, max_jobs: int = 25
    ) -> list[JobSchema]:
        """Scrape a single search using provided page."""
        jobs: list[JobSchema] = []
        search_url = self._build_search_url(query, location)
        logger.info(f"LinkedIn search: {query} in {location}")

        job_ids = await self._extract_job_ids(page, search_url)
        logger.info(f"Found {len(job_ids)} job IDs for '{query}' in {location}")

        for i, job_id in enumerate(job_ids[:max_jobs]):
            try:
                job = await self._fetch_job_detail(page, job_id)
                if job:
                    jobs.append(job)
                if i < len(job_ids) - 1:
                    await self._browser.wait_human(1.5, 3.5)
            except Exception as exc:
                logger.warning(f"Error fetching job {job_id}: {exc}")

        return jobs

    async def _worker_scrape(
        self,
        search_combinations: list[tuple[str, str]],
        worker_id: int,
        max_retries: int = 2,
    ) -> list[JobSchema]:
        """
        Worker that processes a chunk of searches with its own browser.
        Retries on failure up to max_retries times.
        """
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Worker {worker_id}: Starting (attempt {attempt + 1})")
                browser = StealthBrowser(headless=True)
                jobs: list[JobSchema] = []

                async with browser.session() as (_, __, page):
                    for query, location in search_combinations:
                        try:
                            search_jobs = await self._scrape_search_with_page(page, query, location)
                            jobs.extend(search_jobs)
                            # Random delay between searches
                            await asyncio.sleep(random.uniform(2.0, 4.0))
                        except Exception as exc:
                            logger.warning(
                                f"Worker {worker_id} error for '{query}' in '{location}': {exc}"
                            )

                logger.info(f"Worker {worker_id}: Completed with {len(jobs)} jobs")
                return jobs

            except Exception as exc:
                logger.error(f"Worker {worker_id} failed (attempt {attempt + 1}): {exc}")
                if attempt < max_retries:
                    wait_time = random.uniform(5.0, 10.0)
                    logger.info(f"Worker {worker_id}: Retrying in {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Worker {worker_id}: Max retries exceeded")
                    raise

        return []  # Should not reach here

    async def scrape_search(
        self, query: str, location: str, max_pages: int = 3, max_jobs_per_page: int = 25
    ) -> list[JobSchema]:
        """
        Scrape LinkedIn search results across multiple pages.

        Args:
            query: Job search query
            location: Location to search
            max_pages: Number of pages to fetch (default: 3 = 75 jobs)
            max_jobs_per_page: Jobs per page (default: 25)
        """
        all_jobs: list[JobSchema] = []
        async with self._browser.session() as (_, __, page):
            for page_num in range(max_pages):
                start = page_num * max_jobs_per_page
                search_url = self._build_search_url(query, location, start=start)

                logger.info(
                    f"LinkedIn page {page_num + 1}/{max_pages}: {query} in {location} (start={start})"
                )

                job_ids = await self._extract_job_ids(page, search_url)

                if not job_ids:  # No more results
                    logger.info(f"No more jobs found on page {page_num + 1}, stopping")
                    break

                logger.info(f"Found {len(job_ids)} job IDs for '{query}' in {location}")

                # Fetch job details
                for i, job_id in enumerate(job_ids[:max_jobs_per_page]):
                    try:
                        job = await self._fetch_job_detail(page, job_id)
                        if job:
                            all_jobs.append(job)
                        if i < len(job_ids) - 1:
                            await self._browser.wait_human(1.5, 3.5)
                    except Exception as exc:
                        logger.warning(f"Error fetching job {job_id}: {exc}")

                # Delay between pages (5-8 seconds)
                if page_num < max_pages - 1 and job_ids:
                    delay = random.uniform(5.0, 8.0)
                    logger.info(f"Waiting {delay:.1f}s before next page...")
                    await asyncio.sleep(delay)

        logger.info(f"Search complete: {len(all_jobs)} jobs from {max_pages} pages")
        return all_jobs

    async def scrape(
        self,
        queries: list[str] | None = None,
        locations: list[str] | None = None,
        max_workers: int = 6,
    ) -> list[JobSchema]:
        """
        Scrape LinkedIn jobs in parallel using multiple workers.

        Args:
            queries: List of job search queries (defaults to LINKEDIN_SEARCH_QUERIES)
            locations: List of locations (defaults to LINKEDIN_LOCATIONS)
            max_workers: Number of parallel workers (default: 4)
        """
        queries = queries or LINKEDIN_SEARCH_QUERIES
        locations = locations or LINKEDIN_LOCATIONS

        # Create all search combinations
        search_combinations = [(q, l) for q in queries for l in locations]
        logger.info(
            f"LinkedIn scrape: {len(search_combinations)} searches using {max_workers} workers"
        )

        # Split into chunks for workers
        chunks = _split_into_chunks(search_combinations, max_workers)

        # Launch workers with staggered start
        tasks = []
        for worker_id, chunk in enumerate(chunks):
            if not chunk:  # Skip empty chunks
                continue
            task = self._worker_scrape(chunk, worker_id)
            tasks.append(task)

            # Stagger worker starts (10-20 second delay)
            if worker_id < len(chunks) - 1:
                delay = random.uniform(10.0, 20.0)
                logger.info(f"Staggering next worker in {delay:.1f}s...")
                await asyncio.sleep(delay)

        # Wait for all workers to complete
        logger.info(f"Waiting for {len(tasks)} workers to complete...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results
        all_jobs = _combine_results(results)

        # Log summary
        successful_workers = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(
            f"LinkedIn scrape complete: {len(all_jobs)} jobs from "
            f"{successful_workers}/{len(tasks)} successful workers"
        )

        return all_jobs


async def scrape_linkedin(
    queries: list[str] | None = None, locations: list[str] | None = None
) -> list[JobSchema]:
    scraper = LinkedInGuestScraper()
    return await scraper.scrape(queries, locations)
