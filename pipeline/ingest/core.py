from __future__ import annotations

import asyncio
import gc
import html
import json
import logging
import os
import time
import uuid
from collections.abc import AsyncIterator, Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict, cast

# Try to import psutil for memory logging, but make it optional
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

import httpx
from sqlalchemy import case, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.repositories.sqlalchemy_repo import (
    Job,
    JobSource,
)
from pipeline.sources.registry import get_greenhouse_slugs, get_lever_slugs, get_ashby_slugs
from pipeline.sources.greenhouse import GreenhouseClient
from pipeline.sources.lever import LeverClient
from pipeline.sources.ashby import AshbyClient
from pipeline.domain import JobSchema
from pipeline.ingest.deduplication import deduplicate_jobs

logger = logging.getLogger(__name__)
API_FETCH_CONCURRENCY = 10
NOT_FOUND_COOLDOWN_HOURS = 24
SLUG_404_MAX_ENTRIES_PER_SOURCE = 500
SLUG_404_CACHE_PATH = Path(__file__).resolve().parents[1] / "output" / "slug_404_cache.json"


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


class SlugFetchError(TypedDict, total=False):
    step: str
    source: str
    slug: str
    run_id: str | None
    error_type: str
    status_code: int | None
    message: str
    cooldown_until: float


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
        active = {
            slug: expires_at for slug, expires_at in entries.items() if expires_at > now_ts
        }
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


def clean_html_description(text: str) -> str:
    """Decode HTML entities and remove inline styles for cleaner storage."""
    if not text:
        return text

    decoded = html.unescape(text)
    cleaned = re.sub(r' style="[^"]*"', "", decoded)

    return cleaned


import re


def fingerprint_for(job: JobSchema) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, job.apply_url))


async def _fetch_all_apis_parallel(
    *,
    api_fetch_concurrency: int = API_FETCH_CONCURRENCY,
    not_found_cooldown_hours: int = NOT_FOUND_COOLDOWN_HOURS,
    run_id: str | None = None,
    include_errors: bool = False,
) -> (
    tuple[list[JobSchema], list[JobSchema], list[JobSchema]]
    | tuple[list[JobSchema], list[JobSchema], list[JobSchema], list[SlugFetchError]]
):
    """Fetch from all ATS APIs in parallel using thread pool."""
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
    api_fetch_concurrency: int = API_FETCH_CONCURRENCY,
    not_found_cooldown_hours: int = NOT_FOUND_COOLDOWN_HOURS,
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

    greenhouse_jobs, lever_jobs, ashby_jobs = await _fetch_all_apis_parallel(
        api_fetch_concurrency=api_fetch_concurrency,
        not_found_cooldown_hours=not_found_cooldown_hours,
        run_id=run_id,
    )

    logger.info(f"Fetched {len(greenhouse_jobs)} Greenhouse, {len(lever_jobs)} Lever, {len(ashby_jobs)} Ashby jobs")

    return greenhouse_jobs, lever_jobs, ashby_jobs


async def _fetch_source_jobs_streamed(
    source_name: str,
    slugs: list[str],
    fetch_func: Callable[[str], list[JobSchema]],
    *,
    chunk_size: int = 500,
    api_fetch_concurrency: int = API_FETCH_CONCURRENCY,
    not_found_cooldown_hours: int = NOT_FOUND_COOLDOWN_HOURS,
    run_id: str | None = None,
) -> AsyncIterator[list[JobSchema]]:
    """Fetch jobs for a single source in chunks, yielding each chunk as it completes.

    This bounds peak memory to roughly one chunk of jobs plus a small set of
    concurrent coroutines, instead of materializing results for all slugs at once.
    """
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
        yield chunk_jobs

    slug_404_cache = _prune_slug_404_cache(slug_404_cache)
    _save_slug_404_cache(slug_404_cache)

    if fetch_errors:
        per_source: dict[str, int] = {}
        for error in fetch_errors:
            per_source[error["source"]] = per_source.get(error["source"], 0) + 1
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
    chunk_size: int = 500,
    api_fetch_concurrency: int = API_FETCH_CONCURRENCY,
    not_found_cooldown_hours: int = NOT_FOUND_COOLDOWN_HOURS,
    run_id: str | None = None,
) -> int:
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
    try:
        for source_name, slugs, client in (
            ("Greenhouse", gh_slugs, greenhouse),
            ("Lever", lever_slugs, lever),
            ("Ashby", ashby_slugs, ashby),
        ):
            source_total = 0
            chunk_index = 0
            async for chunk in _fetch_source_jobs_streamed(
                source_name=source_name,
                slugs=slugs,
                fetch_func=client.fetch_jobs,
                chunk_size=chunk_size,
                api_fetch_concurrency=api_fetch_concurrency,
                not_found_cooldown_hours=not_found_cooldown_hours,
                run_id=run_id,
            ):
                if chunk:
                    await upsert_jobs(db, chunk, deduplicate=False)
                    total_fetched += len(chunk)
                    source_total += len(chunk)
                chunk_index += 1
                await asyncio.sleep(0)
            logger.info("Fetched %d %s jobs in %d chunk(s)", source_total, source_name, chunk_index)
    finally:
        _close_api_clients(greenhouse, lever, ashby)

    logger.info("Streamed ingestion complete: %d jobs processed", total_fetched)
    return total_fetched


async def mark_all_jobs_inactive(session: AsyncSession) -> int:
    """Mark all active jobs as inactive before ingestion.

    This is part of the sync model: before fetching from APIs, we mark all
    jobs as inactive. Jobs that still exist in the API will be re-activated
    during upsert. Jobs that no longer exist will stay inactive and be deleted.

    Returns:
        Number of jobs marked inactive
    """
    result = await session.execute(update(Job).where(Job.is_active.is_(True), Job.source != JobSource.manual).values(is_active=False))
    await session.commit()
    count = result.rowcount
    if count > 0:
        logger.info(f"Marked {count} jobs as inactive (preparing for sync)")
    return count


async def reactivate_inactive_jobs(session: AsyncSession) -> int:
    """Reactivate non-manual jobs after an unsafe sync is detected.

    This is a rollback helper for the mass inactive mark. It is intentionally
    broad because the sync marker is currently only represented by is_active.
    """
    result = await session.execute(
        update(Job)
        .where(Job.is_active.is_(False), Job.source != JobSource.manual)
        .values(is_active=True)
    )
    await session.commit()
    count = result.rowcount
    if count > 0:
        logger.warning("Reactivated %s inactive jobs after unsafe sync guard triggered", count)
    return count


async def upsert_jobs(db: AsyncSession, jobs: list[JobSchema], deduplicate: bool = True) -> None:
    """Upsert jobs to database using async session."""
    if not jobs:
        return

    unique_jobs = deduplicate_jobs(jobs) if deduplicate else jobs

    if deduplicate and len(unique_jobs) < len(jobs):
        logger.info(f"Deduped {len(jobs) - len(unique_jobs)} jobs within batch ({len(unique_jobs)} unique)")

    BATCH_SIZE = 250
    total_upserted = 0

    for i in range(0, len(unique_jobs), BATCH_SIZE):
        batch = unique_jobs[i : i + BATCH_SIZE]
        rows = []

        for job in batch:
            rows.append(
                {
                    "fingerprint": fingerprint_for(job),
                    "source": JobSource(job.source),
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "apply_url": job.apply_url,
                    "description_text": clean_html_description(job.description_text),
                    "description_embedding": job.description_embedding,
                    "job_category": job.job_category,
                    "job_type": job.job_type,
                    "work_mode": job.work_mode,
                    "posted_at": job.posted_at,
                    "is_active": True,
                }
            )

        stmt = insert(Job).values(rows)
        excluded = stmt.excluded
        stmt = stmt.on_conflict_do_update(
            index_elements=[Job.fingerprint],
            set_={
                "location": excluded.location,
                "description_text": case(
                    (
                        Job.description_text.is_distinct_from(excluded.description_text),
                        excluded.description_text,
                    ),
                    else_=Job.description_text,
                ),
                "embedding_skip_reason": case(
                    (
                        Job.description_text.is_distinct_from(excluded.description_text),
                        None,
                    ),
                    else_=Job.embedding_skip_reason,
                ),
                "embedding_skipped_at": case(
                    (
                        Job.description_text.is_distinct_from(excluded.description_text),
                        None,
                    ),
                    else_=Job.embedding_skipped_at,
                ),
                "job_type": case(
                    (Job.job_type.is_(None), excluded.job_type),
                    else_=Job.job_type,
                ),
                "work_mode": case(
                    (Job.work_mode.is_(None), excluded.work_mode),
                    else_=Job.work_mode,
                ),
                "last_seen": datetime.now(timezone.utc),
                "is_active": True,
            },
        )

        await db.execute(stmt)
        await db.commit()

        # Memory management: expunge objects from session and yield to event loop
        db.expunge_all()
        await asyncio.sleep(0)

        total_upserted += len(rows)
        batch_num = i // BATCH_SIZE + 1
        logger.info(f"Upserted batch {batch_num}: {len(rows)} jobs (total: {total_upserted}/{len(unique_jobs)})")

        # Every 10 batches: force garbage collection
        if batch_num % 10 == 0:
            gc.collect()

        # Every 50 batches: log memory usage
        if batch_num % 50 == 0:
            _log_memory_usage(batch_num)
