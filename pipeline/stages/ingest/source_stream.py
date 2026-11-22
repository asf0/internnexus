"""Concurrent per-source board fetching and fetch-result construction.

This module turns a source's slug list into a stream of ``BoardFetchResult``
values, preserving company-board boundaries so the reconciler can retain an
old board on transient failure without writing every other board.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass

from pipeline.domain import JobSchema
from pipeline.domain.sync_result import SourceFetchStats
from pipeline.stages.ingest.fetch_one import SlugFetchError, fetch_one
from pipeline.stages.ingest.slug_cooldown import (
    load_slug_404_cache,
    partition_cooldown_slugs,
    prune_slug_404_cache,
    save_slug_404_cache,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BoardFetchResult:
    source: str
    slug: str
    jobs: list[JobSchema]
    error: SlugFetchError | None = None


def log_suppressed_slugs(
    source_name: str, stats: SourceFetchStats, transient_suppressed_count: int, retired_suppressed_count: int
) -> None:
    if transient_suppressed_count > 0:
        # Cooldown entries represent boards we did not observe this run. Keep
        # the source incomplete so their existing jobs cannot be deleted.
        for _ in range(transient_suppressed_count):
            stats.record_error("http_404")
        logger.info(
            "%s: preserving %d slug(s) during first-404 cooldown",
            source_name,
            transient_suppressed_count,
        )
    if retired_suppressed_count > 0:
        logger.info(
            "%s: suppressing %d slug(s) after confirmed 404",
            source_name,
            retired_suppressed_count,
        )


def retired_board_result(source_name: str, slug: str, run_id: str | None) -> BoardFetchResult:
    return BoardFetchResult(
        source=source_name.lower(),
        slug=slug,
        jobs=[],
        error={
            "step": "ingest",
            "source": source_name.lower(),
            "slug": slug,
            "run_id": run_id,
            "error_type": "http_404_confirmed",
            "status_code": 404,
        },
    )


def log_fetch_errors(source_name: str, fetch_errors: list[SlugFetchError], run_id: str | None) -> None:
    if not fetch_errors:
        return
    per_source: dict[str, int] = {}
    for error in fetch_errors:
        per_source[error["source"]] = per_source.get(error["source"], 0) + 1
        if error["error_type"] not in {"http_404", "http_404_confirmed"}:
            logger.warning(
                "Slug fetch failed: source=%s slug=%s status=%s type=%s",
                error["source"],
                error["slug"],
                error.get("status_code"),
                error["error_type"],
                extra={
                    "step": error["step"],
                    "source": error["source"],
                    "slug": error["slug"],
                    "run_id": error.get("run_id"),
                },
            )
    logger.warning(
        "%s fetch error summary: total=%d per_source=%s",
        source_name,
        len(fetch_errors),
        per_source,
        extra={
            "step": "ingest",
            "source": source_name.lower(),
            "slug": "*",
            "run_id": run_id,
        },
    )


async def fetch_source_jobs_streamed(
    source_name: str,
    slugs: list[str],
    fetch_func: Callable[[str], list[JobSchema]],
    *,
    chunk_size: int,
    api_fetch_concurrency: int,
    not_found_cooldown_hours: int,
    run_id: str | None = None,
    stats: SourceFetchStats | None = None,
) -> AsyncIterator[BoardFetchResult]:
    """Fetch one source concurrently while preserving company-board boundaries.

    Each yielded result is authoritative only for its own slug. This lets the
    snapshot reconciler retain an old board on transient failure without forcing
    writes for every other board in the source.
    """
    stats = stats or SourceFetchStats(source=source_name.lower(), configured_slugs=len(slugs))
    now_ts = time.time()
    slug_404_cache = load_slug_404_cache()
    source_cache = slug_404_cache.setdefault(source_name.lower(), {})

    active_slugs, retired_slugs, transient_suppressed_count = partition_cooldown_slugs(
        slugs, source_cache, now_ts
    )
    log_suppressed_slugs(source_name, stats, transient_suppressed_count, len(retired_slugs))

    for slug in retired_slugs:
        yield retired_board_result(source_name, slug, run_id)

    if not active_slugs:
        return

    semaphore = asyncio.Semaphore(max(1, api_fetch_concurrency))
    cache_lock = asyncio.Lock()
    fetch_errors: list[SlugFetchError] = []

    async def _fetch_one(slug: str) -> tuple[list[JobSchema], SlugFetchError | None]:
        return await fetch_one(
            slug=slug,
            fetch_func=fetch_func,
            semaphore=semaphore,
            source_name=source_name,
            source_404_cache=source_cache,
            cache_lock=cache_lock,
            cooldown_hours=not_found_cooldown_hours,
            run_id=run_id,
        )

    for i in range(0, len(active_slugs), chunk_size):
        batch_slugs = active_slugs[i : i + chunk_size]
        results = await asyncio.gather(*[_fetch_one(slug) for slug in batch_slugs])
        for slug, (source_jobs, error) in zip(batch_slugs, results, strict=True):
            if error is not None:
                fetch_errors.append(error)
                stats.record_error(error.get("error_type", "unknown"))
            stats.jobs_fetched += len(source_jobs)
            yield BoardFetchResult(
                source=source_name.lower(),
                slug=slug,
                jobs=source_jobs,
                error=error,
            )
        del results

    slug_404_cache = prune_slug_404_cache(slug_404_cache)
    save_slug_404_cache(slug_404_cache)

    log_fetch_errors(source_name, fetch_errors, run_id)
