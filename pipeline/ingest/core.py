from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any, NotRequired, TypedDict, cast
from uuid import UUID

# Try to import psutil for memory logging, but make it optional
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.repositories.sync_ops import (
    SYNC_BATCH_SIZE,
    batched_mark_stale_jobs_inactive,
)
from pipeline.sources.registry import get_greenhouse_slugs, get_lever_slugs, get_ashby_slugs
from pipeline.sources.greenhouse import GreenhouseClient
from pipeline.sources.lever import LeverClient
from pipeline.sources.ashby import AshbyClient
from pipeline.domain import JobSchema
from pipeline.ingest.result import IngestResult, SourceFetchStats
from pipeline.ingest.upsert import upsert_jobs
from pipeline.runtime.config import get_config

logger = logging.getLogger(__name__)
SLUG_404_MAX_ENTRIES_PER_SOURCE = 500
SLUG_404_CACHE_PATH = Path(__file__).resolve().parents[1] / "output" / "slug_404_cache.json"


def _resolve_api_settings(
    api_fetch_concurrency: int | None,
    not_found_cooldown_hours: int | None,
) -> tuple[int, int]:
    config = get_config().api
    return (
        config.fetch_concurrency if api_fetch_concurrency is None else api_fetch_concurrency,
        config.slug_404_cooldown_hours if not_found_cooldown_hours is None else not_found_cooldown_hours,
    )


def _log_memory_usage(batch_num: int | None = None) -> None:
    """Log current memory usage if psutil is available."""
    if HAS_PSUTIL:
        try:
            process = psutil.Process()
            mem_mb = process.memory_info().rss / 1024 / 1024
            if batch_num is not None:
                logger.info(f"Batch {batch_num}: {mem_mb:.2f} MB")
            else:
                logger.info(f"Memory: {mem_mb:.2f} MB")
        except Exception:  # noqa: BLE001  # memory logging is best-effort
            pass


class SlugFetchError(TypedDict):
    step: str
    source: str
    slug: str
    error_type: str
    run_id: NotRequired[str | None]
    status_code: NotRequired[int | None]
    message: NotRequired[str]
    cooldown_until: NotRequired[float]


def _load_slug_404_cache() -> dict[str, dict[str, float]]:
    """Load slug -> expiry timestamp cache for 404 cooldown suppression."""
    if not SLUG_404_CACHE_PATH.exists():
        return {}
    try:
        with open(SLUG_404_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        normalized: dict[str, dict[str, float]] = {}
        for source, source_map in data.items():
            if not isinstance(source_map, dict):
                continue
            normalized[source] = {}
            for slug, expires_at in source_map.items():
                try:
                    normalized[source][slug] = float(expires_at)
                except (TypeError, ValueError):
                    continue
        return normalized
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        logger.debug("Failed to load slug 404 cache: %s", exc)
        return {}


def _prune_slug_404_cache(
    cache: dict[str, dict[str, float]],
    max_entries: int = SLUG_404_MAX_ENTRIES_PER_SOURCE,
) -> dict[str, dict[str, float]]:
    """Remove expired entries and cap per-source entry count.

    Keeps the most-recently expiring entries when a source exceeds the cap.
    """
    now_ts = time.time()
    pruned: dict[str, dict[str, float]] = {}
    for source, entries in cache.items():
        active = {slug: expires_at for slug, expires_at in entries.items() if expires_at > now_ts}
        if not active:
            continue
        if len(active) > max_entries:
            sorted_active = sorted(active.items(), key=lambda item: item[1], reverse=True)
            active = dict(sorted_active[:max_entries])
        pruned[source] = active
    return pruned


def _save_slug_404_cache(cache: dict[str, dict[str, float]]) -> None:
    """Persist 404 cooldown cache to disk atomically."""
    try:
        SLUG_404_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = SLUG_404_CACHE_PATH.parent / f"{SLUG_404_CACHE_PATH.name}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(cache, f)
        os.replace(tmp_path, SLUG_404_CACHE_PATH)
    except (OSError, TypeError) as exc:
        logger.debug("Failed to save slug 404 cache: %s", exc)


async def _fetch_all_apis_parallel(
    *,
    api_fetch_concurrency: int | None = None,
    not_found_cooldown_hours: int | None = None,
    run_id: str | None = None,
    include_errors: bool = False,
) -> (
    tuple[list[JobSchema], list[JobSchema], list[JobSchema]]
    | tuple[list[JobSchema], list[JobSchema], list[JobSchema], list[SlugFetchError]]
):
    """Fetch from all ATS APIs in parallel using thread pool."""
    api_fetch_concurrency, not_found_cooldown_hours = _resolve_api_settings(
        api_fetch_concurrency,
        not_found_cooldown_hours,
    )

    greenhouse = GreenhouseClient()
    lever = LeverClient()
    ashby = AshbyClient()

    try:
        gh_slugs = get_greenhouse_slugs()
        lever_slugs = get_lever_slugs()
        ashby_slugs = get_ashby_slugs()

        slug_404_cache = _load_slug_404_cache()
        cache_lock = asyncio.Lock()

        async def _fetch_source_jobs(
            source_name: str, slugs: list[str], fetch_func: Callable[[str], list[JobSchema]]
        ) -> tuple[list[JobSchema], list[SlugFetchError]]:
            semaphore = asyncio.Semaphore(max(1, api_fetch_concurrency))
            now_ts = time.time()
            source_cache = slug_404_cache.setdefault(source_name.lower(), {})
            active_slugs: list[str] = []
            suppressed_count = 0
            source_errors: list[SlugFetchError] = []

            for slug in slugs:
                expires_at = source_cache.get(slug)
                if expires_at and expires_at > now_ts:
                    suppressed_count += 1
                    continue
                active_slugs.append(slug)

            if suppressed_count > 0:
                logger.info(
                    "%s: suppressing %d slug(s) currently in 404 cooldown",
                    source_name,
                    suppressed_count,
                )

            async def _fetch_one(slug: str) -> tuple[list[JobSchema], SlugFetchError | None]:
                async with semaphore:
                    try:
                        return await asyncio.to_thread(fetch_func, slug), None
                    except httpx.HTTPStatusError as exc:
                        status_code = exc.response.status_code if exc.response is not None else 0
                        if status_code == 404:
                            cooldown_until = time.time() + (max(1, not_found_cooldown_hours) * 3600)
                            async with cache_lock:
                                slug_404_cache.setdefault(source_name.lower(), {})[slug] = cooldown_until
                            logger.info(
                                "%s slug '%s' returned 404; skipping for %dh",
                                source_name,
                                slug,
                                max(1, not_found_cooldown_hours),
                            )
                            return [], {
                                "step": "ingest",
                                "source": source_name.lower(),
                                "slug": slug,
                                "run_id": run_id,
                                "error_type": "http_404",
                                "status_code": 404,
                                "message": str(exc),
                                "cooldown_until": cooldown_until,
                            }
                        return [], {
                            "step": "ingest",
                            "source": source_name.lower(),
                            "slug": slug,
                            "run_id": run_id,
                            "error_type": "http_error",
                            "status_code": status_code,
                            "message": str(exc),
                        }
                    except Exception as exc:  # noqa: BLE001  # catch-all to record per-slug failure without crashing ingest
                        return [], {
                            "step": "ingest",
                            "source": source_name.lower(),
                            "slug": slug,
                            "run_id": run_id,
                            "error_type": "exception",
                            "status_code": None,
                            "message": str(exc),
                        }

            results = await asyncio.gather(*[_fetch_one(slug) for slug in active_slugs], return_exceptions=False)
            jobs: list[JobSchema] = []
            for source_jobs, error in results:
                jobs.extend(source_jobs)
                if error is not None:
                    source_errors.append(error)
            return jobs, source_errors

        results = await asyncio.gather(
            _fetch_source_jobs("Greenhouse", gh_slugs, greenhouse.fetch_jobs),
            _fetch_source_jobs("Lever", lever_slugs, lever.fetch_jobs),
            _fetch_source_jobs("Ashby", ashby_slugs, ashby.fetch_jobs),
            return_exceptions=True,
        )

        greenhouse_jobs: list[JobSchema] = []
        lever_jobs: list[JobSchema] = []
        ashby_jobs: list[JobSchema] = []
        fetch_errors: list[SlugFetchError] = []

        for idx, source_name in enumerate(("greenhouse", "lever", "ashby")):
            result = results[idx]
            if isinstance(result, tuple):
                source_jobs, source_errors = result
                if source_name == "greenhouse":
                    greenhouse_jobs = cast(list[JobSchema], source_jobs)
                elif source_name == "lever":
                    lever_jobs = cast(list[JobSchema], source_jobs)
                else:
                    ashby_jobs = cast(list[JobSchema], source_jobs)
                fetch_errors.extend(source_errors)

        slug_404_cache = _prune_slug_404_cache(slug_404_cache)
        _save_slug_404_cache(slug_404_cache)

        for error in fetch_errors:
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

        if fetch_errors:
            per_source: dict[str, int] = {}
            for error in fetch_errors:
                per_source[error["source"]] = per_source.get(error["source"], 0) + 1
            logger.warning(
                "API fetch error summary: total=%d per_source=%s",
                len(fetch_errors),
                per_source,
                extra={
                    "step": "ingest",
                    "source": "all",
                    "slug": "*",
                    "run_id": run_id,
                },
            )

        if include_errors:
            return greenhouse_jobs, lever_jobs, ashby_jobs, fetch_errors
        return greenhouse_jobs, lever_jobs, ashby_jobs
    finally:
        _close_api_clients(greenhouse, lever, ashby)


def _close_api_clients(*clients: Any) -> None:
    """Best-effort close for ATS clients."""
    for client in clients:
        close = getattr(client, "close", None)
        if callable(close):
            try:
                close()
            except Exception as exc:  # noqa: BLE001  # client close is best-effort
                logger.warning("Failed to close %s client: %s", client.__class__.__name__, exc)


async def fetch_api_jobs(
    *,
    api_fetch_concurrency: int | None = None,
    not_found_cooldown_hours: int | None = None,
    run_id: str | None = None,
) -> tuple[list[JobSchema], list[JobSchema], list[JobSchema]]:
    """Fetch jobs from all 3 ATS platforms in parallel.

    Returns a 3-tuple of (greenhouse_jobs, lever_jobs, ashby_jobs) so callers
    can upsert and free each source list independently, avoiding a peak where
    all three lists plus a merged copy are alive simultaneously.
    """
    gh_slugs = get_greenhouse_slugs()
    lever_slugs = get_lever_slugs()
    ashby_slugs = get_ashby_slugs()

    logger.info(
        f"Fetching {len(gh_slugs)} Greenhouse, {len(lever_slugs)} Lever, {len(ashby_slugs)} Ashby companies in parallel..."
    )

    greenhouse_jobs, lever_jobs, ashby_jobs = cast(
        tuple[list[JobSchema], list[JobSchema], list[JobSchema]],
        await _fetch_all_apis_parallel(
            api_fetch_concurrency=api_fetch_concurrency,
            not_found_cooldown_hours=not_found_cooldown_hours,
            run_id=run_id,
        ),
    )

    logger.info(f"Fetched {len(greenhouse_jobs)} Greenhouse, {len(lever_jobs)} Lever, {len(ashby_jobs)} Ashby jobs")

    return greenhouse_jobs, lever_jobs, ashby_jobs


async def _fetch_source_jobs_streamed(
    source_name: str,
    slugs: list[str],
    fetch_func: Callable[[str], list[JobSchema]],
    *,
    chunk_size: int,
    api_fetch_concurrency: int,
    not_found_cooldown_hours: int,
    run_id: str | None = None,
    stats: SourceFetchStats | None = None,
) -> AsyncIterator[list[JobSchema]]:
    """Fetch jobs for a single source in chunks, yielding each chunk as it completes.

    This bounds peak memory to roughly one chunk of jobs plus a small set of
    concurrent coroutines, instead of materializing results for all slugs at once.
    """
    stats = stats or SourceFetchStats(source=source_name.lower(), configured_slugs=len(slugs))
    now_ts = time.time()
    slug_404_cache = _load_slug_404_cache()
    source_cache = slug_404_cache.setdefault(source_name.lower(), {})
    active_slugs: list[str] = []
    suppressed_count = 0

    for slug in slugs:
        expires_at = source_cache.get(slug)
        if expires_at and expires_at > now_ts:
            suppressed_count += 1
            continue
        active_slugs.append(slug)

    if suppressed_count > 0:
        logger.info(
            "%s: suppressing %d slug(s) currently in 404 cooldown",
            source_name,
            suppressed_count,
        )

    if not active_slugs:
        return

    semaphore = asyncio.Semaphore(max(1, api_fetch_concurrency))
    cache_lock = asyncio.Lock()
    fetch_errors: list[SlugFetchError] = []

    async def _fetch_one(slug: str) -> tuple[list[JobSchema], SlugFetchError | None]:
        async with semaphore:
            try:
                return await asyncio.to_thread(fetch_func, slug), None
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code if exc.response is not None else 0
                if status_code == 404:
                    cooldown_until = time.time() + (max(1, not_found_cooldown_hours) * 3600)
                    async with cache_lock:
                        slug_404_cache.setdefault(source_name.lower(), {})[slug] = cooldown_until
                    logger.info(
                        "%s slug '%s' returned 404; skipping for %dh",
                        source_name,
                        slug,
                        max(1, not_found_cooldown_hours),
                    )
                    return [], {
                        "step": "ingest",
                        "source": source_name.lower(),
                        "slug": slug,
                        "run_id": run_id,
                        "error_type": "http_404",
                        "status_code": 404,
                        "message": str(exc),
                        "cooldown_until": cooldown_until,
                    }
                return [], {
                    "step": "ingest",
                    "source": source_name.lower(),
                    "slug": slug,
                    "run_id": run_id,
                    "error_type": "http_error",
                    "status_code": status_code,
                    "message": str(exc),
                }
            except Exception as exc:  # noqa: BLE001  # catch-all to record per-slug failure without crashing ingest
                return [], {
                    "step": "ingest",
                    "source": source_name.lower(),
                    "slug": slug,
                    "run_id": run_id,
                    "error_type": "exception",
                    "status_code": None,
                    "message": str(exc),
                }

    for i in range(0, len(active_slugs), chunk_size):
        batch_slugs = active_slugs[i : i + chunk_size]
        results = await asyncio.gather(*[_fetch_one(slug) for slug in batch_slugs])
        chunk_jobs: list[JobSchema] = []
        for source_jobs, error in results:
            chunk_jobs.extend(source_jobs)
            if error is not None:
                fetch_errors.append(error)
                stats.record_error(error.get("error_type", "unknown"))
        stats.jobs_fetched += len(chunk_jobs)
        del results
        yield chunk_jobs
        del chunk_jobs

    slug_404_cache = _prune_slug_404_cache(slug_404_cache)
    _save_slug_404_cache(slug_404_cache)

    if fetch_errors:
        per_source: dict[str, int] = {}
        for error in fetch_errors:
            per_source[error["source"]] = per_source.get(error["source"], 0) + 1
            if error["error_type"] != "http_404":
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


async def fetch_and_ingest_streamed(
    db: AsyncSession,
    *,
    chunk_size: int,
    upsert_batch_size: int,
    api_fetch_concurrency: int,
    not_found_cooldown_hours: int,
    sync_id: UUID,
) -> IngestResult:
    """Fetch jobs from all sources in chunks and upsert each chunk immediately.

    Processes sources sequentially and yields control back to the event loop after
    every chunk so memory stays bounded regardless of total job count.
    """
    gh_slugs = get_greenhouse_slugs()
    lever_slugs = get_lever_slugs()
    ashby_slugs = get_ashby_slugs()

    logger.info(
        "Fetching %d Greenhouse, %d Lever, %d Ashby companies in streamed chunks of %d slugs...",
        len(gh_slugs),
        len(lever_slugs),
        len(ashby_slugs),
        chunk_size,
    )

    greenhouse = GreenhouseClient()
    lever = LeverClient()
    ashby = AshbyClient()

    total_fetched = 0
    total_changed = 0
    source_stats: dict[str, SourceFetchStats] = {}
    try:
        for source_name, slugs, client in (
            ("Greenhouse", gh_slugs, greenhouse),
            ("Lever", lever_slugs, lever),
            ("Ashby", ashby_slugs, ashby),
        ):
            source_key = source_name.lower()
            stats = SourceFetchStats(source=source_key, configured_slugs=len(slugs))
            source_stats[source_key] = stats
            source_total = 0
            chunk_index = 0
            async for chunk in _fetch_source_jobs_streamed(
                source_name=source_name,
                slugs=slugs,
                fetch_func=client.fetch_jobs,
                chunk_size=chunk_size,
                api_fetch_concurrency=api_fetch_concurrency,
                not_found_cooldown_hours=not_found_cooldown_hours,
                run_id=str(sync_id),
                stats=stats,
            ):
                chunk_job_count = len(chunk)
                if chunk_job_count:
                    upsert_stats = await upsert_jobs(
                        db,
                        chunk,
                        sync_id=sync_id,
                        deduplicate=True,
                        batch_size=upsert_batch_size,
                    )
                    total_changed += upsert_stats.changed
                    total_fetched += chunk_job_count
                    source_total += chunk_job_count
                chunk_index += 1
                _log_memory_usage(chunk_index)
                del chunk
                await asyncio.sleep(0)
            logger.info("Fetched %d %s jobs in %d chunk(s)", source_total, source_name, chunk_index)
    finally:
        _close_api_clients(greenhouse, lever, ashby)

    logger.info(
        "Streamed ingestion complete: %d jobs processed, %d inserted/changed/reactivated",
        total_fetched,
        total_changed,
    )
    return IngestResult(
        sync_id=sync_id,
        total_fetched=total_fetched,
        source_counts={source: stats.jobs_fetched for source, stats in source_stats.items()},
        fetch_error_counts={source: stats.fetch_errors for source, stats in source_stats.items()},
        source_complete={source: stats.complete for source, stats in source_stats.items()},
        jobs_changed=total_changed,
    )


async def mark_stale_jobs_inactive(
    session: AsyncSession,
    sync_id: UUID,
    batch_size: int | None = None,
    max_attempts: int | None = None,
    base_delay: float | None = None,
    max_delay: float | None = None,
) -> int:
    """Mark active non-manual jobs that were not seen this run as inactive.

    Uses the run-scoped sightings table to identify jobs not observed this run.

    Args:
        session: SQLAlchemy async session.
        sync_id: Synchronization run whose sightings define active jobs.
        batch_size: Number of rows per batch. Defaults to SYNC_BATCH_SIZE.
        max_attempts: Maximum retry attempts. Defaults to 3.
        base_delay: Base delay in seconds. Defaults to 0.5.
        max_delay: Maximum delay in seconds. Defaults to 4.0.

    Returns:
        Number of jobs marked inactive.
    """
    if batch_size is None:
        batch_size = SYNC_BATCH_SIZE
    return await batched_mark_stale_jobs_inactive(
        session,
        sync_id,
        batch_size=batch_size,
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
    )
