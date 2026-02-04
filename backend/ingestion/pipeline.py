from __future__ import annotations

import hashlib
import html
import logging
import re
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Job, JobSource
from .apis.company_registry import COMPANY_REGISTRY
from .apis.greenhouse_client import GreenhouseClient
from .apis.lever_client import LeverClient
from .schemas import JobSchema

logger = logging.getLogger(__name__)


def clean_html_description(text: str) -> str:
    """Decode HTML entities and remove inline styles for cleaner storage."""
    if not text:
        return text
    
    # Decode HTML entities (&lt; -> <, &gt; -> >, etc.)
    decoded = html.unescape(text)
    
    # Remove inline style attributes to avoid conflicts with frontend styling
    cleaned = re.sub(r' style="[^"]*"', '', decoded)
    
    return cleaned


def fingerprint_for(job: JobSchema) -> str:
    payload = f"{job.company.lower()}|{job.title.lower()}|{job.location.lower()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fetch_api_jobs() -> list[JobSchema]:
    greenhouse = GreenhouseClient()
    lever = LeverClient()
    jobs: list[JobSchema] = []

    for slug in COMPANY_REGISTRY:
        try:
            jobs.extend(greenhouse.fetch_jobs(slug))
        except Exception as exc:  # pragma: no cover - network errors
            logger.warning("Greenhouse failed for %s: %s", slug, exc)

        try:
            jobs.extend(lever.fetch_jobs(slug))
        except Exception as exc:  # pragma: no cover - network errors
            logger.warning("Lever failed for %s: %s", slug, exc)

    return jobs


def upsert_jobs(db: Session, jobs: list[JobSchema]) -> None:
    if not jobs:
        return

    # Deduplicate jobs within the input list (keep last occurrence)
    seen_fingerprints = {}
    unique_jobs = []
    for job in jobs:
        fp = fingerprint_for(job)
        if fp not in seen_fingerprints:
            unique_jobs.append(job)
            seen_fingerprints[fp] = len(unique_jobs) - 1
    
    if len(unique_jobs) < len(jobs):
        logger.info(f"Deduped {len(jobs) - len(unique_jobs)} jobs within batch ({len(unique_jobs)} unique)")
    
    # Batch inserts to avoid exceeding PostgreSQL parameter limit (65535)
    BATCH_SIZE = 100
    total_upserted = 0
    
    for i in range(0, len(unique_jobs), BATCH_SIZE):
        batch = unique_jobs[i:i + BATCH_SIZE]
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
        stmt = stmt.on_conflict_do_update(
            index_elements=[Job.fingerprint],
            set_={"last_seen": datetime.utcnow(), "is_active": True},
        )
        db.execute(stmt)
        db.commit()
        total_upserted += len(rows)
        logger.info(f"Upserted batch {i//BATCH_SIZE + 1}: {len(rows)} jobs (total: {total_upserted}/{len(unique_jobs)})")
