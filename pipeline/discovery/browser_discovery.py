"""Browser discovery using Playwright with stealth and adaptive rate limiting."""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from playwright_stealth import Stealth

from .browser_config import (
    BLOCK_INDICATORS,
    GOOGLE_SEARCH_URL,
    JOB_BOARDS,
    COUNTRIES,
    MAX_PAGES_PER_SEARCH,
    MAX_RETRIES,
    MIN_DELAY,
    MAX_DELAY,
    NEXT_PAGE_SELECTOR,
    OUTPUT_DIR,
    OUTPUT_FILE,
    RESULT_SELECTOR,
    RETRY_BACKOFF_BASE,
    SEARCHES_PER_BATCH,
    TIMEOUT,
    VISIBLE_MODE,
)
from .progress_tracker import (
    add_companies,
    get_remaining_queries,
    load_progress,
    mark_query_complete,
    save_progress,
    update_delay,
)
from .user_agents import get_random_user_agent

logger = logging.getLogger(__name__)


class DiscoveryBrowser:
    """Browser wrapper for discovery with stealth and retry logic."""

    def __init__(self) -> None:
        self._stealth = Stealth()
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._user_agent_config: dict | None = None

    async def launch(self) -> None:
        """Launch browser with random user agent."""
        self._user_agent_config = get_random_user_agent()

        logger.info(
            f"Launching browser with user agent: {self._user_agent_config['user_agent'][:50]}..."
        )

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=not VISIBLE_MODE,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ]
            if VISIBLE_MODE
            else [],
        )

        self._context = await self._browser.new_context(
            user_agent=self._user_agent_config["user_agent"],
            viewport=self._user_agent_config["viewport"],
            locale=self._user_agent_config["locale"],
        )

        self._page = await self._context.new_page()
        await self._stealth.apply_stealth_async(self._page)

    async def close(self) -> None:
        """Close browser and cleanup."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if hasattr(self, "_playwright"):
            await self._playwright.stop()
        logger.info("Browser closed")

    async def search_google(
        self,
        query: str,
        max_pages: int = MAX_PAGES_PER_SEARCH,
    ) -> tuple[list[str], bool]:
        """Search Google and extract all result URLs.

        Args:
            query: Search query string
            max_pages: Maximum pages to fetch

        Returns:
            Tuple of (list of URLs, was_blocked boolean)
        """
        all_urls = []
        was_blocked = False

        for attempt in range(MAX_RETRIES):
            try:
                # Build search URL
                search_url = f"{GOOGLE_SEARCH_URL}?q={query.replace(' ', '+')}"

                logger.info(f"Searching: {query} (attempt {attempt + 1})")
                await self._page.goto(search_url, timeout=TIMEOUT)

                # Wait for results to load
                await asyncio.sleep(random.uniform(2, 4))

                # Check for blocking
                if await self._is_blocked():
                    logger.warning("Google blocking detected!")
                    was_blocked = True
                    break

                # Extract URLs from all pages
                page_num = 1
                seen_urls = set()

                while page_num <= max_pages:
                    logger.info(f"Processing page {page_num}")

                    # Extract URLs from current page
                    urls = await self._extract_urls_from_page()
                    new_urls = [url for url in urls if url not in seen_urls]

                    if not new_urls:
                        logger.info("No new URLs found, moving to next query")
                        break

                    all_urls.extend(new_urls)
                    seen_urls.update(new_urls)
                    logger.info(f"Found {len(new_urls)} new URLs (total: {len(all_urls)})")

                    # Try to go to next page
                    has_next = await self._go_to_next_page()
                    if not has_next:
                        logger.info("No more pages available")
                        break

                    page_num += 1
                    await asyncio.sleep(random.uniform(1, 3))

                return all_urls, False

            except Exception as e:
                logger.error(f"Search failed (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_BACKOFF_BASE**attempt
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Max retries exceeded")
                    return all_urls, True

        return all_urls, was_blocked

    async def _is_blocked(self) -> bool:
        """Check if Google is blocking the search."""
        try:
            content = await self._page.content()
            content_lower = content.lower()

            for indicator in BLOCK_INDICATORS:
                if indicator.lower() in content_lower:
                    return True

            return False
        except Exception:
            return False

    async def _extract_urls_from_page(self) -> list[str]:
        """Extract all result URLs from current page."""
        urls = []

        try:
            # Find all result links
            links = await self._page.query_selector_all(RESULT_SELECTOR)

            for link in links:
                href = await link.get_attribute("href")
                if href and href.startswith("http"):
                    # Clean up Google redirect URLs
                    if "google.com/url" in href:
                        parsed = urlparse(href)
                        params = parse_qs(parsed.query)
                        if "url" in params:
                            href = unquote(params["url"][0])

                    urls.append(href)

            return urls

        except Exception as e:
            logger.error(f"Failed to extract URLs: {e}")
            return []

    async def _go_to_next_page(self) -> bool:
        """Click next page button if available."""
        try:
            next_button = await self._page.query_selector(NEXT_PAGE_SELECTOR)
            if next_button:
                await next_button.click()
                await asyncio.sleep(random.uniform(2, 4))
                return True
            return False
        except Exception:
            return False


def extract_company_slug(url: str, job_board: str) -> str | None:
    """Extract company slug from job board URL.

    Examples:
        https://jobs.lever.co/stripe/abc-123 -> stripe
        https://boards.greenhouse.io/databricks/jobs/456 -> databricks
    """
    try:
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")

        if not path_parts:
            return None

        domain = JOB_BOARDS.get(job_board, "")

        # Check if URL matches the job board domain
        if domain not in parsed.netloc:
            return None

        # Extract slug (first path segment)
        slug = path_parts[0]

        # Validate slug (should be alphanumeric with hyphens/underscores)
        if slug and re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", slug):
            return slug.lower()

        return None

    except Exception as e:
        logger.debug(f"Failed to extract slug from {url}: {e}")
        return None


async def random_delay(min_delay: float, max_delay: float) -> None:
    """Sleep for a random duration."""
    delay = random.uniform(min_delay, max_delay)
    logger.debug(f"Sleeping for {delay:.1f}s")
    await asyncio.sleep(delay)


async def discover_with_browser() -> dict[str, set[str]]:
    """Main discovery function using browser.

    Returns:
        Dict mapping ATS name to set of company slugs
    """
    # Load progress
    progress = load_progress()

    # Check if already complete
    if progress["metadata"]["status"] == "complete":
        logger.info("Discovery already complete!")
        return {k: set(v) for k, v in progress["companies"].items()}

    # Build all queries
    all_queries = []
    for country in COUNTRIES:
        for board in JOB_BOARDS:
            all_queries.append((country, board))

    total_queries = len(all_queries)
    progress["metadata"]["total_batches"] = total_queries

    # Get remaining queries
    remaining = get_remaining_queries(progress, all_queries)
    completed = len(all_queries) - len(remaining)

    logger.info(
        f"Starting discovery: {completed}/{total_queries} completed, {len(remaining)} remaining"
    )

    if not remaining:
        logger.info("All queries already completed!")
        progress["metadata"]["status"] = "complete"
        save_progress(progress)
        return {k: set(v) for k, v in progress["companies"].items()}

    # Process all queries with single browser instance
    batch_number = 0
    was_blocked = False

    browser = DiscoveryBrowser()
    try:
        await browser.launch()

        while remaining and not was_blocked:
            batch_number += 1

            # Take next batch
            batch = remaining[:SEARCHES_PER_BATCH]
            remaining = remaining[SEARCHES_PER_BATCH:]

            logger.info(f"\n{'=' * 60}")
            logger.info(f"Processing batch {batch_number}: {len(batch)} queries")
            logger.info(f"{'=' * 60}")

            for country, board in batch:
                # Build query
                domain = JOB_BOARDS[board]
                query = f"{country} site:{domain}"

                # Get current delay
                current_delay = progress["metadata"]["current_delay"]

                # Search
                urls, blocked = await browser.search_google(query)

                if blocked:
                    logger.error("Google blocked the search! Waiting for user...")
                    logger.info(
                        "Please solve any CAPTCHA in the browser window, then press Enter to continue..."
                    )
                    input()  # Wait for user to press Enter

                    # Retry this query
                    urls, blocked = await browser.search_google(query)

                    if blocked:
                        logger.error("Still blocked after user intervention. Stopping.")
                        was_blocked = True
                        update_delay(progress, increase=True)
                        break

                # Extract company slugs
                companies = set()
                for url in urls:
                    slug = extract_company_slug(url, board)
                    if slug:
                        companies.add(slug)

                # Add to progress
                new_count = add_companies(progress, board, companies)
                mark_query_complete(progress, country, board)

                logger.info(
                    f"Found {len(companies)} companies ({new_count} new) for {country} ({board})"
                )

                # Save progress after each query
                save_progress(progress)

                # Save output file after each query
                save_discovered_companies({k: set(v) for k, v in progress["companies"].items()})

                # Random delay between queries
                await random_delay(MIN_DELAY, max(MAX_DELAY, current_delay))

                # Reset delay on success
                if progress["metadata"]["current_delay"] > MIN_DELAY:
                    progress["metadata"]["current_delay"] = MIN_DELAY

            # Save batch progress
            save_progress(progress)

            # Delay between batches (longer delay)
            if remaining:
                logger.info(f"Batch {batch_number} complete. Waiting before next batch...")
                await random_delay(MAX_DELAY, MAX_DELAY + 5)

    finally:
        await browser.close()

    # Final status
    if was_blocked:
        progress["metadata"]["status"] = "blocked"
        logger.error("Discovery stopped due to blocking")
    elif not remaining:
        progress["metadata"]["status"] = "complete"
        logger.info("Discovery complete!")

    save_progress(progress)

    # Return results
    return {k: set(v) for k, v in progress["companies"].items()}


def save_discovered_companies(
    companies_by_ats: dict[str, set[str]],
    output_path: Path | None = None,
) -> None:
    """Save discovered companies to final JSON file."""
    if output_path is None:
        output_dir = Path(__file__).parent / OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / OUTPUT_FILE

    existing_data = {"lever": [], "greenhouse": [], "ashby": []}
    if output_path.exists():
        try:
            with open(output_path) as f:
                data = json.load(f)
                if isinstance(data, dict):
                    existing_data.update(data)
        except Exception as e:
            logger.warning(f"Could not load existing file: {e}")

    # Merge and deduplicate
    final_data = {}
    all_ats = set(existing_data.keys()) | set(companies_by_ats.keys())

    for ats in all_ats:
        existing_set = set(existing_data.get(ats, []))
        new_set = companies_by_ats.get(ats, set())
        final_data[ats] = sorted(list(existing_set | new_set))

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(final_data, f, indent=2)

    total = sum(len(v) for v in final_data.values())
    logger.info(f"Saved {total} companies to {output_path}")
    for ats, companies in final_data.items():
        logger.info(f"  {ats}: {len(companies)} companies")


async def main():
    """CLI entry point for browser discovery."""
    import json

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("\n" + "=" * 60)
    print("BROWSER DISCOVERY")
    print("=" * 60)
    print("This will search Google for companies on job boards.")
    print(f"Countries: {', '.join(COUNTRIES)}")
    print(f"Job boards: {', '.join(JOB_BOARDS.keys())}")
    print(f"Total searches: {len(COUNTRIES) * len(JOB_BOARDS)}")
    print("=" * 60 + "\n")

    # Run discovery
    results = await discover_with_browser()

    # Save to final output file
    save_discovered_companies(results)

    # Print summary
    print("\n" + "=" * 60)
    print("DISCOVERY SUMMARY")
    print("=" * 60)
    total = 0
    for ats, companies in results.items():
        print(f"  {ats:12}: {len(companies):4} companies")
        total += len(companies)
    print(f"  {'TOTAL':12}: {total:4} companies")
    print(f"\nOutput saved to: {OUTPUT_DIR}/{OUTPUT_FILE}")

    # Load progress to show status
    progress = load_progress()
    if progress["metadata"]["status"] == "complete":
        print("\n✅ Discovery is COMPLETE")
    elif progress["metadata"]["status"] == "blocked":
        print("\n⚠️  Discovery was BLOCKED - run again to resume")
    else:
        print("\n⏸️  Discovery PAUSED - run again to resume")


if __name__ == "__main__":
    asyncio.run(main())
