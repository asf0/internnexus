from __future__ import annotations

import asyncio
import html
import json
import logging
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import httpx
from sqlalchemy import case, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.repositories.sqlalchemy_repo import (
    AshbyJobMetadata,
    GreenhouseJobMetadata,
    Job,
    JobSource,
    LeverJobMetadata,
)
from pipeline.apis.company_registry import get_greenhouse_slugs, get_lever_slugs, get_ashby_slugs
from pipeline.apis.greenhouse_client import GreenhouseClient
from pipeline.apis.lever_client import LeverClient
from pipeline.apis.ashby_client import AshbyClient
from pipeline.schemas import JobSchema
from pipeline.utils.deduplication import deduplicate_jobs

logger = logging.getLogger(__name__)
API_FETCH_CONCURRENCY = 10
NOT_FOUND_COOLDOWN_HOURS = 24
SLUG_404_CACHE_PATH = Path(__file__).parent / "output" / "slug_404_cache.json"


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
    except Exception as exc:
        logger.debug("Failed to load slug 404 cache: %s", exc)
        return {}


def _save_slug_404_cache(cache: dict[str, dict[str, float]]) -> None:
    """Persist 404 cooldown cache to disk."""
    try:
        SLUG_404_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SLUG_404_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f)
    except Exception as exc:
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
) -> tuple[list[JobSchema], list[JobSchema], list[JobSchema]]:
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
        ) -> list[JobSchema]:
            semaphore = asyncio.Semaphore(max(1, api_fetch_concurrency))
            now_ts = time.time()
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

            async def _fetch_one(slug: str) -> list[JobSchema]:
                async with semaphore:
                    try:
                        return await asyncio.to_thread(fetch_func, slug)
                    except httpx.HTTPStatusError as exc:
                        status_code = exc.response.status_code if exc.response is not None else 0
                        if status_code == 404:
                            cooldown_until = time.time() + (max(1, not_found_cooldown_hours) * 3600)
                            async with cache_lock:
                                slug_404_cache.setdefault(source_name.lower(), {})[slug] = (
                                    cooldown_until
                                )
                            logger.info(
                                "%s slug '%s' returned 404; skipping for %dh",
                                source_name,
                                slug,
                                max(1, not_found_cooldown_hours),
                            )
                            return []
                        logger.warning("%s failed for %s: %s", source_name, slug, exc)
                        return []
                    except Exception as exc:
                        logger.warning("%s failed for %s: %s", source_name, slug, exc)
                        return []

            results = await asyncio.gather(
                *[_fetch_one(slug) for slug in active_slugs], return_exceptions=False
            )
            jobs: list[JobSchema] = []
            for result in results:
                jobs.extend(result)
            return jobs

        results = await asyncio.gather(
            _fetch_source_jobs("Greenhouse", gh_slugs, greenhouse.fetch_jobs),
            _fetch_source_jobs("Lever", lever_slugs, lever.fetch_jobs),
            _fetch_source_jobs("Ashby", ashby_slugs, ashby.fetch_jobs),
            return_exceptions=True,
        )

        greenhouse_jobs = cast(list[JobSchema], results[0]) if isinstance(results[0], list) else []
        lever_jobs = cast(list[JobSchema], results[1]) if isinstance(results[1], list) else []
        ashby_jobs = cast(list[JobSchema], results[2]) if isinstance(results[2], list) else []

        now_ts = time.time()
        for source in list(slug_404_cache.keys()):
            source_entries = slug_404_cache[source]
            slug_404_cache[source] = {
                slug: expires_at
                for slug, expires_at in source_entries.items()
                if expires_at > now_ts
            }
            if not slug_404_cache[source]:
                del slug_404_cache[source]
        _save_slug_404_cache(slug_404_cache)

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
            except Exception as exc:
                logger.warning("Failed to close %s client: %s", client.__class__.__name__, exc)


async def fetch_api_jobs(
    *,
    api_fetch_concurrency: int = API_FETCH_CONCURRENCY,
    not_found_cooldown_hours: int = NOT_FOUND_COOLDOWN_HOURS,
) -> list[JobSchema]:
    """Fetch jobs from all 3 ATS platforms in parallel."""
    gh_slugs = get_greenhouse_slugs()
    lever_slugs = get_lever_slugs()
    ashby_slugs = get_ashby_slugs()

    logger.info(
        f"Fetching {len(gh_slugs)} Greenhouse, {len(lever_slugs)} Lever, {len(ashby_slugs)} Ashby companies in parallel..."
    )

    greenhouse_jobs, lever_jobs, ashby_jobs = await _fetch_all_apis_parallel(
        api_fetch_concurrency=api_fetch_concurrency,
        not_found_cooldown_hours=not_found_cooldown_hours,
    )

    all_jobs = greenhouse_jobs + lever_jobs + ashby_jobs
    logger.info(
        f"Fetched {len(greenhouse_jobs)} Greenhouse, {len(lever_jobs)} Lever, {len(ashby_jobs)} Ashby jobs"
    )

    return all_jobs


async def mark_all_jobs_inactive(session: AsyncSession) -> int:
    """Mark all active jobs as inactive before ingestion.

    This is part of the sync model: before fetching from APIs, we mark all
    jobs as inactive. Jobs that still exist in the API will be re-activated
    during upsert. Jobs that no longer exist will stay inactive and be deleted.

    Returns:
        Number of jobs marked inactive
    """
    result = await session.execute(update(Job).where(Job.is_active == True).values(is_active=False))
    await session.commit()
    count = result.rowcount
    if count > 0:
        logger.info(f"Marked {count} jobs as inactive (preparing for sync)")
    return count


async def upsert_metadata_batch(
    db: AsyncSession,
    fp_to_id: dict[str, uuid.UUID],
    jobs: list[JobSchema],
    table_class: Any,
    field_mapping: dict[str, str | Callable[[JobSchema], Any]],
    update_fields: list[str],
) -> int:
    if not jobs:
        return 0

    rows: list[dict[str, Any]] = []
    for job in jobs:
        fp = fingerprint_for(job)
        job_id = fp_to_id.get(fp)
        if not job_id:
            continue
        row: dict[str, Any] = {"job_id": job_id}
        for col_name, source in field_mapping.items():
            if callable(source):
                row[col_name] = source(job)
            else:
                val = getattr(job, source, None)
                row[col_name] = val
        rows.append(row)

    if not rows:
        return 0

    stmt = insert(table_class).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[table_class.job_id],
        set_={f: getattr(stmt.excluded, f) for f in update_fields},
    )
    await db.execute(stmt)
    return len(rows)


GREENHOUSE_FIELD_MAPPING: dict[str, str | Callable[[JobSchema], Any]] = {
    "external_id": "external_id",
    "internal_job_id": lambda j: j.internal_job_id or 0,
    "requisition_id": "requisition_id",
    "education": "education",
    "language": lambda j: j.language or "en",
    "first_published": "first_published",
    "updated_at": "updated_at",
    "departments": lambda j: j.departments or [],
    "offices": lambda j: j.offices or [],
    "data_compliance": lambda j: j.data_compliance or [],
    "hosted_url": "hosted_url",
}

LEVER_FIELD_MAPPING: dict[str, str | Callable[[JobSchema], Any]] = {
    "external_id": "external_id",
    "commitment": "commitment",
    "department": "department",
    "team": "team",
    "all_locations": lambda j: j.all_locations or [],
    "workplace_type": "workplace_type",
    "salary_min": "salary_min",
    "salary_max": "salary_max",
    "salary_currency": "salary_currency",
    "salary_interval": "salary_interval",
    "salary_description": "salary_description",
    "description_html": "description_html",
    "description_plain": "description_plain",
    "requirements": lambda j: j.requirements or [],
    "requirements_html": "requirements_html",
    "requirements_plain": "requirements_plain",
    "has_requirements": lambda j: j.has_requirements or False,
    "hosted_url": "hosted_url",
    "created_at_raw": lambda j: j.created_at_raw or 0,
}

ASHBY_FIELD_MAPPING: dict[str, str | Callable[[JobSchema], Any]] = {
    "external_id": "external_id",
    "department": "department",
    "team": "team",
    "employment_type": "employment_type",
    "location_raw": "location_raw",
    "address_locality": "address_locality",
    "address_region": "address_region",
    "address_country": "address_country",
    "is_remote": "is_remote",
    "description_html": "description_html",
    "description_plain": "description_plain",
    "job_url": "job_url",
    "compensation": lambda j: j.compensation or {},
    "is_listed": lambda j: j.is_listed or True,
    "updated_at": "updated_at",
}


async def upsert_greenhouse_metadata_batch(
    db: AsyncSession, fp_to_id: dict[str, uuid.UUID], jobs: list[JobSchema]
) -> int:
    return await upsert_metadata_batch(
        db,
        fp_to_id,
        jobs,
        GreenhouseJobMetadata,
        GREENHOUSE_FIELD_MAPPING,
        ["updated_at", "departments", "offices"],
    )


async def upsert_lever_metadata_batch(
    db: AsyncSession, fp_to_id: dict[str, uuid.UUID], jobs: list[JobSchema]
) -> int:
    return await upsert_metadata_batch(
        db,
        fp_to_id,
        jobs,
        LeverJobMetadata,
        LEVER_FIELD_MAPPING,
        ["requirements", "requirements_html", "requirements_plain"],
    )


async def upsert_ashby_metadata_batch(
    db: AsyncSession, fp_to_id: dict[str, uuid.UUID], jobs: list[JobSchema]
) -> int:
    return await upsert_metadata_batch(
        db,
        fp_to_id,
        jobs,
        AshbyJobMetadata,
        ASHBY_FIELD_MAPPING,
        ["updated_at", "compensation"],
    )


async def upsert_jobs(db: AsyncSession, jobs: list[JobSchema], deduplicate: bool = True) -> None:
    """Upsert jobs to database using async session."""
    if not jobs:
        return

    unique_jobs = deduplicate_jobs(jobs) if deduplicate else jobs

    if deduplicate and len(unique_jobs) < len(jobs):
        logger.info(
            f"Deduped {len(jobs) - len(unique_jobs)} jobs within batch ({len(unique_jobs)} unique)"
        )

    BATCH_SIZE = 250
    total_upserted = 0

    for i in range(0, len(unique_jobs), BATCH_SIZE):
        batch = unique_jobs[i : i + BATCH_SIZE]
        rows = []
        greenhouse_jobs: list[JobSchema] = []
        lever_jobs: list[JobSchema] = []
        ashby_jobs: list[JobSchema] = []

        for job in batch:
            if job.source == "greenhouse":
                greenhouse_jobs.append(job)
            elif job.source == "lever":
                lever_jobs.append(job)
            elif job.source == "ashby":
                ashby_jobs.append(job)

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
        ).returning(Job.id, Job.fingerprint)

        result = await db.execute(stmt)
        returned_rows = result.fetchall()

        fp_to_id = {row.fingerprint: row.id for row in returned_rows}

        if greenhouse_jobs:
            await upsert_greenhouse_metadata_batch(db, fp_to_id, greenhouse_jobs)
        if lever_jobs:
            await upsert_lever_metadata_batch(db, fp_to_id, lever_jobs)
        if ashby_jobs:
            await upsert_ashby_metadata_batch(db, fp_to_id, ashby_jobs)

        await db.commit()
        total_upserted += len(rows)
        logger.info(
            f"Upserted batch {i // BATCH_SIZE + 1}: {len(rows)} jobs (total: {total_upserted}/{len(unique_jobs)})"
        )
