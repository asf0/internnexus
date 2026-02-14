from __future__ import annotations

import html
import logging
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import case
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, JobSource
from .apis.company_registry import COMPANY_REGISTRY
from .apis.greenhouse_client import GreenhouseClient
from .apis.lever_client import LeverClient
from .apis.workday_client import WorkdayClient
from .apis.ashby_client import AshbyClient
from .apis.smartrecruiters_client import SmartRecruitersClient
from .schemas import JobSchema

logger = logging.getLogger(__name__)


def clean_html_description(text: str) -> str:
    """Decode HTML entities and remove inline styles for cleaner storage."""
    if not text:
        return text

    decoded = html.unescape(text)
    cleaned = re.sub(r' style="[^"]*"', "", decoded)

    return cleaned


def fingerprint_for(job: JobSchema) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, job.apply_url))


def fetch_api_jobs() -> list[JobSchema]:
    greenhouse = GreenhouseClient()
    lever = LeverClient()
    workday = WorkdayClient()
    ashby = AshbyClient()
    smartrecruiters = SmartRecruitersClient()
    jobs: list[JobSchema] = []

    for slug in COMPANY_REGISTRY:
        try:
            jobs.extend(greenhouse.fetch_jobs(slug))
        except Exception as exc:
            logger.warning("Greenhouse failed for %s: %s", slug, exc)

        try:
            jobs.extend(lever.fetch_jobs(slug))
        except Exception as exc:
            logger.warning("Lever failed for %s: %s", slug, exc)

    workday_jobs = workday.fetch_all_tenants()
    logger.info(f"Fetched {len(workday_jobs)} jobs from Workday")
    jobs.extend(workday_jobs)

    ashby_jobs = ashby.fetch_all_slugs()
    logger.info(f"Fetched {len(ashby_jobs)} jobs from Ashby")
    jobs.extend(ashby_jobs)

    sr_jobs = smartrecruiters.fetch_all_slugs()
    logger.info(f"Fetched {len(sr_jobs)} jobs from SmartRecruiters")
    jobs.extend(sr_jobs)

    return jobs


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
                    "visa_sponsored": job.visa_sponsored,
                    "f1_friendly": job.f1_friendly,
                    "job_category": job.job_category,
                    "requires_sponsorship": job.requires_sponsorship,
                    "requires_us_citizenship": job.requires_us_citizenship,
                    "application_closed": job.application_closed,
                    "is_faang_plus": job.is_faang_plus,
                    "requires_advanced_degree": job.requires_advanced_degree,
                    "posted_at": job.posted_at,
                    "is_active": True,
                }
            )

        stmt = insert(Job).values(rows)
        excluded = stmt.excluded
        stmt = stmt.on_conflict_do_update(
            index_elements=[Job.fingerprint],
            set_={
                "description_text": case(
                    (
                        Job.description_text.is_distinct_from(excluded.description_text),
                        excluded.description_text,
                    ),
                    else_=Job.description_text,
                ),
                "last_seen": datetime.now(timezone.utc),
                "is_active": True,
            },
        )
        await db.execute(stmt)
        await db.commit()
        total_upserted += len(rows)
        logger.info(
            f"Upserted batch {i // BATCH_SIZE + 1}: {len(rows)} jobs (total: {total_upserted}/{len(unique_jobs)})"
        )
