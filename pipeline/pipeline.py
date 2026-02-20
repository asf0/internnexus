from __future__ import annotations

import html
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import case, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import (
    Job,
    JobSource,
    GreenhouseJobMetadata,
    LeverJobMetadata,
    AshbyJobMetadata,
)
from pipeline.apis.company_registry import get_greenhouse_slugs, get_lever_slugs, get_ashby_slugs
from pipeline.apis.greenhouse_client import GreenhouseClient
from pipeline.apis.lever_client import LeverClient
from pipeline.apis.ashby_client import AshbyClient
from pipeline.schemas import JobSchema

logger = logging.getLogger(__name__)


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


def fetch_api_jobs() -> list[JobSchema]:
    """Fetch jobs from all 3 ATS platforms using browser-discovered companies."""
    greenhouse = GreenhouseClient()
    lever = LeverClient()
    ashby = AshbyClient()
    jobs: list[JobSchema] = []

    gh_slugs = get_greenhouse_slugs()
    logger.info(f"Fetching {len(gh_slugs)} Greenhouse companies...")
    for slug in gh_slugs:
        try:
            jobs.extend(greenhouse.fetch_jobs(slug))
        except Exception as exc:
            logger.warning("Greenhouse failed for %s: %s", slug, exc)

    lever_slugs = get_lever_slugs()
    logger.info(f"Fetching {len(lever_slugs)} Lever companies...")
    for slug in lever_slugs:
        try:
            jobs.extend(lever.fetch_jobs(slug))
        except Exception as exc:
            logger.warning("Lever failed for %s: %s", slug, exc)

    ashby_slugs = get_ashby_slugs()
    logger.info(f"Fetching {len(ashby_slugs)} Ashby companies...")
    for slug in ashby_slugs:
        try:
            jobs.extend(ashby.fetch_jobs(slug))
        except Exception as exc:
            logger.warning("Ashby failed for %s: %s", slug, exc)

    return jobs


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


async def upsert_greenhouse_metadata_batch(
    db: AsyncSession, fp_to_id: dict[str, uuid.UUID], jobs: list[JobSchema]
) -> int:
    """Bulk upsert Greenhouse-specific metadata."""
    if not jobs:
        return 0

    rows = []
    for job in jobs:
        fp = fingerprint_for(job)
        job_id = fp_to_id.get(fp)
        if not job_id:
            continue
        rows.append(
            {
                "job_id": job_id,
                "external_id": job.external_id or "",
                "internal_job_id": job.internal_job_id or 0,
                "requisition_id": job.requisition_id or "",
                "education": job.education,
                "language": job.language or "en",
                "first_published": job.first_published,
                "updated_at": job.updated_at,
                "departments": job.departments or [],
                "offices": job.offices or [],
                "data_compliance": job.data_compliance or [],
                "hosted_url": job.hosted_url or "",
            }
        )

    if not rows:
        return 0

    stmt = insert(GreenhouseJobMetadata).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[GreenhouseJobMetadata.job_id],
        set_={
            "updated_at": stmt.excluded.updated_at,
            "departments": stmt.excluded.departments,
            "offices": stmt.excluded.offices,
        },
    )
    await db.execute(stmt)
    return len(rows)


async def upsert_lever_metadata_batch(
    db: AsyncSession, fp_to_id: dict[str, uuid.UUID], jobs: list[JobSchema]
) -> int:
    """Bulk upsert Lever-specific metadata."""
    if not jobs:
        return 0

    rows = []
    for job in jobs:
        fp = fingerprint_for(job)
        job_id = fp_to_id.get(fp)
        if not job_id:
            continue
        rows.append(
            {
                "job_id": job_id,
                "external_id": job.external_id or "",
                "commitment": job.commitment or "",
                "department": job.department or "",
                "team": job.team or "",
                "all_locations": job.all_locations or [],
                "workplace_type": job.workplace_type or "",
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "salary_currency": job.salary_currency,
                "salary_interval": job.salary_interval,
                "salary_description": job.salary_description,
                "description_html": job.description_html or "",
                "description_plain": job.description_plain or "",
                "requirements": job.requirements or [],
                "requirements_html": job.requirements_html,
                "requirements_plain": job.requirements_plain,
                "has_requirements": job.has_requirements or False,
                "hosted_url": job.hosted_url or "",
                "created_at_raw": job.created_at_raw or 0,
            }
        )

    if not rows:
        return 0

    stmt = insert(LeverJobMetadata).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[LeverJobMetadata.job_id],
        set_={
            "requirements": stmt.excluded.requirements,
            "requirements_html": stmt.excluded.requirements_html,
            "requirements_plain": stmt.excluded.requirements_plain,
        },
    )
    await db.execute(stmt)
    return len(rows)


async def upsert_ashby_metadata_batch(
    db: AsyncSession, fp_to_id: dict[str, uuid.UUID], jobs: list[JobSchema]
) -> int:
    """Bulk upsert Ashby-specific metadata."""
    if not jobs:
        return 0

    rows = []
    for job in jobs:
        fp = fingerprint_for(job)
        job_id = fp_to_id.get(fp)
        if not job_id:
            continue
        rows.append(
            {
                "job_id": job_id,
                "external_id": job.external_id or "",
                "department": job.department or "",
                "team": job.team or "",
                "employment_type": job.employment_type or "",
                "location_raw": job.location_raw or "",
                "address_locality": job.address_locality or "",
                "address_region": job.address_region or "",
                "address_country": job.address_country or "",
                "is_remote": job.is_remote,
                "description_html": job.description_html or "",
                "description_plain": job.description_plain or "",
                "job_url": job.job_url or "",
                "compensation": job.compensation or {},
                "is_listed": job.is_listed or True,
                "updated_at": job.updated_at,
            }
        )

    if not rows:
        return 0

    stmt = insert(AshbyJobMetadata).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[AshbyJobMetadata.job_id],
        set_={
            "updated_at": stmt.excluded.updated_at,
            "compensation": stmt.excluded.compensation,
        },
    )
    await db.execute(stmt)
    return len(rows)


async def upsert_jobs(db: AsyncSession, jobs: list[JobSchema]) -> None:
    """Upsert jobs to database using async session."""
    if not jobs:
        return

    seen_fingerprints = {}
    unique_jobs = []
    for job in jobs:
        fp = fingerprint_for(job)
        if fp not in seen_fingerprints:
            unique_jobs.append(job)
            seen_fingerprints[fp] = len(unique_jobs) - 1

    if len(unique_jobs) < len(jobs):
        logger.info(
            f"Deduped {len(jobs) - len(unique_jobs)} jobs within batch ({len(unique_jobs)} unique)"
        )

    BATCH_SIZE = 100
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
                    "city": job.city,
                    "state": job.state,
                    "country": job.country,
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

        greenhouse_jobs = [j for j in batch if j.source == "greenhouse"]
        lever_jobs = [j for j in batch if j.source == "lever"]
        ashby_jobs = [j for j in batch if j.source == "ashby"]

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
