"""Company discovery backed by a SearxNG instance."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from pipeline.runtime.config import get_config

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(os.environ.get("DISCOVERY_OUTPUT_DIR", str(Path(__file__).parent / "output")))
DISCOVERED_COMPANIES_FILE = OUTPUT_DIR / "discovered_companies.json"
PROGRESS_FILE = OUTPUT_DIR / "discovery_progress.json"

DEFAULT_COUNTRIES = [
    "United States",
    "Brazil",
    "Korea",
    "Ireland",
    "Canada",
    "United Kingdom",
    "Germany",
]

ATS_DOMAINS = {
    "lever": "jobs.lever.co",
    "greenhouse": "boards.greenhouse.io",
    "ashby": "jobs.ashbyhq.com",
}

ATS_DOMAIN_ALIASES = {
    "lever": {"jobs.lever.co"},
    "greenhouse": {"boards.greenhouse.io", "job-boards.greenhouse.io"},
    "ashby": {"jobs.ashbyhq.com"},
}

MIN_EXISTING_COMPANIES_FOR_SHRINK_GUARD = 100
MIN_DISCOVERY_RETENTION_RATIO = 0.75

RESERVED_SLUGS = {"embed", "jobs", "job", "job_board", "job_app"}


def _default_progress() -> dict[str, Any]:
    return {
        "metadata": {
            "completed_queries": 0,
            "total_queries": 0,
            "last_updated": None,
            "status": "not_started",
        },
        "completed_queries": [],
        "exhausted_queries": [],
        "companies": {ats: [] for ats in ATS_DOMAINS},
    }


def load_progress(file_path: Path | None = None) -> dict[str, Any]:
    """Load discovery progress from disk."""
    path = file_path or PROGRESS_FILE
    default = _default_progress()

    if not path.exists():
        return default

    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not load discovery progress: %s", exc)
        return default

    if not isinstance(data, dict):
        return default

    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    companies = data.get("companies")
    if not isinstance(companies, dict):
        companies = {}
    completed_queries = data.get("completed_queries")
    if not isinstance(completed_queries, list):
        completed_queries = []
    exhausted_queries = data.get("exhausted_queries")
    if not isinstance(exhausted_queries, list):
        exhausted_queries = []

    merged = _default_progress()
    merged["metadata"].update(metadata)
    merged["completed_queries"] = list(completed_queries)
    merged["exhausted_queries"] = list(exhausted_queries)

    for ats in ATS_DOMAINS:
        values = companies.get(ats, [])
        if isinstance(values, list):
            merged["companies"][ats] = values

    return merged


def save_progress(progress: dict[str, Any], file_path: Path | None = None) -> None:
    """Persist discovery progress to disk."""
    path = file_path or PROGRESS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    progress["metadata"]["completed_queries"] = len(progress.get("completed_queries", []))
    progress["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()

    with path.open("w", encoding="utf-8") as fh:
        json.dump(progress, fh, indent=2)


def _normalize_companies_output(data: Any) -> dict[str, set[str]]:
    if not isinstance(data, dict):
        return {ats: set() for ats in ATS_DOMAINS}

    output: dict[str, set[str]] = {}
    for ats in ATS_DOMAINS:
        values = data.get(ats, [])
        output[ats] = {value for value in values if isinstance(value, str)} if isinstance(values, list) else set()
    return output


def load_discovered_companies(output_path: Path | None = None) -> dict[str, set[str]]:
    """Load the persisted discovery output."""
    path = output_path or DISCOVERED_COMPANIES_FILE
    if not path.exists():
        return {ats: set() for ats in ATS_DOMAINS}

    try:
        with path.open("r", encoding="utf-8") as fh:
            return _normalize_companies_output(json.load(fh))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not load existing discovery output: %s", exc)
        return {ats: set() for ats in ATS_DOMAINS}


def _company_count(companies_by_ats: dict[str, set[str]]) -> int:
    return sum(len(companies_by_ats.get(ats, set())) for ats in ATS_DOMAINS)


def _should_keep_previous_discovery_output(
    previous: dict[str, set[str]],
    current: dict[str, set[str]],
) -> bool:
    previous_count = _company_count(previous)
    current_count = _company_count(current)
    if previous_count < MIN_EXISTING_COMPANIES_FOR_SHRINK_GUARD:
        return False
    return current_count < previous_count * MIN_DISCOVERY_RETENTION_RATIO


def save_discovered_companies(
    companies_by_ats: dict[str, set[str]],
    output_path: Path | None = None,
) -> None:
    """Replace discovered companies in the format consumed by company_registry."""
    path = output_path or DISCOVERED_COMPANIES_FILE
    path.parent.mkdir(parents=True, exist_ok=True)

    output = {
        ats: sorted(value for value in companies_by_ats.get(ats, set()) if isinstance(value, str))
        for ats in ATS_DOMAINS
    }

    with path.open("w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2)


def _valid_slug(slug: str) -> str | None:
    slug = slug.lower()
    if slug in RESERVED_SLUGS:
        return None
    if re.fullmatch(r"[a-z0-9][a-z0-9_-]*", slug):
        return slug
    return None


def extract_company_slug(url: str, ats: str) -> str | None:
    """Extract a company slug from an ATS-hosted job URL."""
    expected_domains = ATS_DOMAIN_ALIASES.get(ats, set())
    if not expected_domains:
        return None

    if not isinstance(url, str):
        return None
    try:
        parsed = urlparse(url)
    except (TypeError, ValueError):
        return None

    hostname = (parsed.hostname or "").lower()
    if hostname not in expected_domains:
        return None

    path_parts = [part for part in parsed.path.strip("/").split("/") if part]
    if ats == "greenhouse" and path_parts == ["embed", "job_board"]:
        board_slug = parse_qs(parsed.query).get("for", [None])[0]
        return _valid_slug(board_slug) if isinstance(board_slug, str) else None

    if not path_parts:
        return None

    return _valid_slug(path_parts[0])


def _build_search_queries(countries: list[str]) -> list[tuple[str, str, str]]:
    queries: list[tuple[str, str, str]] = []
    for ats, domain in ATS_DOMAINS.items():
        queries.append(("global", ats, f'site:{domain} intext:"apply"'))
        for country in countries:
            queries.append((country, ats, f'site:{domain} {country} intext:"apply"'))
    return queries


def _base_query_key(scope: str, ats: str) -> str:
    return f"{scope}|{ats}"


def _query_key(scope: str, ats: str, page: int) -> str:
    return f"{scope}|{ats}|page:{page}"


def _configured_max_pages(config: Any) -> int | None:
    raw_value = getattr(config, "max_pages", None)
    if raw_value in (None, ""):
        return None

    value = int(raw_value)
    if value <= 0:
        return None
    return value


def _extract_urls(payload: dict[str, Any]) -> list[str]:
    candidates: list[dict[str, Any]] = []
    for key in ("results", "organic_results"):
        value = payload.get(key)
        if isinstance(value, list):
            candidates.extend(item for item in value if isinstance(item, dict))

    urls: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        url = item.get("url") or item.get("link")
        if not isinstance(url, str):
            continue
        if not url.startswith("http"):
            continue
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


async def _search_searxng(
    client: httpx.AsyncClient,
    base_url: str,
    query: str,
    *,
    page: int = 1,
) -> list[str]:
    search_url = base_url.rstrip("/")
    if not search_url.endswith("/search"):
        search_url = f"{search_url}/search"

    response = await client.get(
        search_url,
        params={"q": query, "format": "json", "pageno": page},
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("unexpected SearxNG response payload")
    urls = _extract_urls(payload)
    unresponsive_engines = payload.get("unresponsive_engines")
    if not urls and isinstance(unresponsive_engines, list) and unresponsive_engines:
        raise RuntimeError(f"SearxNG returned no URLs with unresponsive engines: {unresponsive_engines}")
    return urls


async def discover_companies(
    *,
    output_path: Path | None = None,
    progress_path: Path | None = None,
) -> dict[str, set[str]]:
    """Discover ATS company slugs by querying SearxNG."""
    config = get_config().discovery
    output_file = output_path or DISCOVERED_COMPANIES_FILE
    progress_file = progress_path or PROGRESS_FILE

    if not config.enabled:
        logger.info("Discovery disabled; reusing existing company registry")
        from pipeline.sources.registry import get_all_slugs_by_ats

        return {ats: set(values) for ats, values in get_all_slugs_by_ats().items()}

    if not config.searxng_url:
        raise ValueError("Discovery is enabled but discovery.searxng_url is not configured")

    progress = load_progress(progress_file)
    if progress.get("metadata", {}).get("status") == "complete":
        logger.info("Previous discovery was complete; starting a fresh discovery refresh")
        progress = _default_progress()

    countries = list(DEFAULT_COUNTRIES)
    search_queries = _build_search_queries(countries)
    max_pages = _configured_max_pages(config)
    progress["metadata"]["total_queries"] = len(search_queries) * max_pages if max_pages is not None else None

    completed = {key for key in progress.get("completed_queries", []) if isinstance(key, str)}
    exhausted = {key for key in progress.get("exhausted_queries", []) if isinstance(key, str)}
    progress["completed_queries"] = sorted(completed)
    progress["exhausted_queries"] = sorted(exhausted)

    if all(_base_query_key(scope, ats) in exhausted for scope, ats, _query in search_queries):
        progress["metadata"]["status"] = "complete"
        save_progress(progress, progress_file)
        return {ats: set(progress["companies"].get(ats, [])) for ats in ATS_DOMAINS}

    logger.info(
        "Starting SearxNG discovery against %s: %d search queries, max_pages=%s",
        config.searxng_url,
        len(search_queries),
        max_pages or "until_empty",
    )
    progress["metadata"]["status"] = "running"
    save_progress(progress, progress_file)

    any_query_failed = False
    page = 1
    async with httpx.AsyncClient(timeout=float(config.timeout)) as client:
        while max_pages is None or page <= max_pages:
            progressed = False
            for query_index, (scope, ats, query) in enumerate(search_queries, start=1):
                base_key = _base_query_key(scope, ats)
                if base_key in exhausted:
                    continue

                page_key = _query_key(scope, ats, page)
                if page_key in completed:
                    progressed = True
                    continue

                logger.info(
                    "Discovery query %d/%d: %s page %d",
                    query_index,
                    len(search_queries),
                    query,
                    page,
                )
                try:
                    urls = await _search_searxng(client, config.searxng_url, query, page=page)
                except Exception as exc:  # noqa: BLE001
                    any_query_failed = True
                    logger.warning("Discovery query failed for %s (%s page %d): %s", scope, ats, page, exc)
                    if config.query_delay_seconds > 0:
                        await asyncio.sleep(config.query_delay_seconds)
                    continue

                progressed = True
                completed.add(page_key)
                progress["completed_queries"] = sorted(completed)

                if not urls:
                    exhausted.add(base_key)
                    progress["exhausted_queries"] = sorted(exhausted)
                    save_progress(progress, progress_file)
                    if config.query_delay_seconds > 0:
                        await asyncio.sleep(config.query_delay_seconds)
                    continue

                companies = {slug for url in urls if (slug := extract_company_slug(url, ats))}
                existing = set(progress["companies"].get(ats, []))
                progress["companies"][ats] = sorted(existing | companies)

                save_progress(progress, progress_file)

                if config.query_delay_seconds > 0:
                    await asyncio.sleep(config.query_delay_seconds)

            if all(_base_query_key(scope, ats) in exhausted for scope, ats, _query in search_queries):
                break
            if not progressed:
                break
            page += 1

    if any_query_failed:
        progress["metadata"]["status"] = "partial"
    elif all(_base_query_key(scope, ats) in exhausted for scope, ats, _query in search_queries):
        progress["metadata"]["status"] = "complete"
    else:
        progress["metadata"]["status"] = "capped"
    save_progress(progress, progress_file)

    result = {ats: set(progress["companies"].get(ats, [])) for ats in ATS_DOMAINS}
    previous = load_discovered_companies(output_file)
    if progress["metadata"]["status"] == "complete":
        if _should_keep_previous_discovery_output(previous, result):
            logger.warning(
                "Discovery found only %d companies after previous output had %d; keeping previous output unchanged",
                _company_count(result),
                _company_count(previous),
            )
            return previous
        save_discovered_companies(result, output_file)
        return result

    merged = {ats: previous.get(ats, set()) | result.get(ats, set()) for ats in ATS_DOMAINS}
    if merged != previous:
        logger.warning(
            "Discovery did not complete; merging %d newly discovered companies into previous output",
            _company_count(merged) - _company_count(previous),
        )
        save_discovered_companies(merged, output_file)
    else:
        logger.warning("Discovery did not complete; keeping previous discovered companies output unchanged")
    return merged


async def main() -> None:
    """CLI entry point for company discovery."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    config = get_config().discovery
    print("\n" + "=" * 60)
    print("COMPANY DISCOVERY")
    print("=" * 60)
    print(f"SearxNG URL: {config.searxng_url}")
    print(f"Countries: {', '.join(DEFAULT_COUNTRIES)}")
    print(f"ATS targets: {', '.join(ATS_DOMAINS)}")
    print("=" * 60 + "\n")

    results = await discover_companies()

    print("\n" + "=" * 60)
    print("DISCOVERY SUMMARY")
    print("=" * 60)
    total = 0
    for ats, companies in results.items():
        print(f"  {ats:12}: {len(companies):4} companies")
        total += len(companies)
    print(f"  {'TOTAL':12}: {total:4} companies")
    print(f"\nOutput saved to: {DISCOVERED_COMPANIES_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
