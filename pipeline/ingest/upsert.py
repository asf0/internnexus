"""Changed-only job upserts with atomic run-scoped sighting records."""

from __future__ import annotations

import asyncio
import gc
import html
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import case, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.domain import JobSchema
from pipeline.ingest.deduplication import deduplicate_jobs
from pipeline.ingest.identity import fingerprint_for
from pipeline.models import Job, JobSource, PipelineJobSighting
from pipeline.runtime.config import get_config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UpsertStats:
    seen: int = 0
    changed: int = 0

    def __add__(self, other: UpsertStats) -> UpsertStats:
        return UpsertStats(seen=self.seen + other.seen, changed=self.changed + other.changed)


def clean_html_description(text: str) -> str:
    """Decode HTML entities and remove inline styles for cleaner storage."""
    if not text:
        return text
    return re.sub(r' style="[^"]*"', "", html.unescape(text))


def _job_rows(jobs: list[JobSchema]) -> tuple[list[dict], list[dict]]:
    job_rows: list[dict] = []
    sighting_rows: list[dict] = []
    for job in jobs:
        fingerprint = fingerprint_for(job)
        source = JobSource(job.source)
        job_rows.append(
            {
                "fingerprint": fingerprint,
                "source": source,
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
        sighting_rows.append({"fingerprint": fingerprint, "source": source})
    return job_rows, sighting_rows


def _changed_only_job_upsert(rows: list[dict]):
    stmt = insert(Job).values(rows)
    excluded = stmt.excluded

    title_changed = Job.title.is_distinct_from(excluded.title)
    company_changed = Job.company.is_distinct_from(excluded.company)
    location_changed = Job.location.is_distinct_from(excluded.location)
    description_changed = Job.description_text.is_distinct_from(excluded.description_text)
    posted_at_changed = Job.posted_at.is_distinct_from(excluded.posted_at)
    job_type_changed = Job.job_type.is_distinct_from(excluded.job_type)
    work_mode_changed = Job.work_mode.is_distinct_from(excluded.work_mode)
    reactivated = Job.is_active.is_not(True)
    classification_input_changed = or_(title_changed, description_changed)

    return stmt.on_conflict_do_update(
        index_elements=[Job.fingerprint],
        set_={
            "title": excluded.title,
            "company": excluded.company,
            "location": excluded.location,
            "city": case((location_changed, None), else_=Job.city),
            "state": case((location_changed, None), else_=Job.state),
            "country": case((location_changed, None), else_=Job.country),
            "description_text": excluded.description_text,
            "description_embedding": case(
                (classification_input_changed, None),
                else_=Job.description_embedding,
            ),
            "embedding_skip_reason": case(
                (classification_input_changed, None),
                else_=Job.embedding_skip_reason,
            ),
            "embedding_skipped_at": case(
                (classification_input_changed, None),
                else_=Job.embedding_skipped_at,
            ),
            "job_category": case(
                (classification_input_changed, None),
                else_=Job.job_category,
            ),
            "job_type": excluded.job_type,
            "work_mode": excluded.work_mode,
            "posted_at": excluded.posted_at,
            "last_seen": datetime.now(timezone.utc),
            "is_active": True,
        },
        where=or_(
            title_changed,
            company_changed,
            location_changed,
            description_changed,
            posted_at_changed,
            job_type_changed,
            work_mode_changed,
            reactivated,
        ),
    ).returning(Job.id)


async def upsert_jobs(
    db: AsyncSession,
    jobs: list[JobSchema],
    *,
    sync_id: UUID,
    deduplicate: bool = True,
    batch_size: int | None = None,
) -> UpsertStats:
    """Record sightings and upsert only new, changed, or reactivated jobs."""
    if not jobs:
        return UpsertStats()

    if batch_size is None:
        batch_size = get_config().ingest.upsert_batch_size

    unique_jobs = deduplicate_jobs(jobs) if deduplicate else jobs
    if deduplicate and len(unique_jobs) < len(jobs):
        logger.info("Deduped %d jobs within batch", len(jobs) - len(unique_jobs))
    totals = UpsertStats()
    for i in range(0, len(unique_jobs), batch_size):
        batch = unique_jobs[i : i + batch_size]
        rows, sighting_rows = _job_rows(batch)
        for sighting in sighting_rows:
            sighting["sync_id"] = sync_id

        sightings_stmt = (
            insert(PipelineJobSighting)
            .values(sighting_rows)
            .on_conflict_do_nothing(
                index_elements=[
                    PipelineJobSighting.sync_id,
                    PipelineJobSighting.fingerprint,
                ]
            )
        )
        try:
            await db.execute(sightings_stmt)
            result = await db.execute(_changed_only_job_upsert(rows))
            changed = len(result.fetchall())
            await db.commit()
        except Exception:
            await db.rollback()
            raise

        db.expunge_all()
        await asyncio.sleep(0)
        totals += UpsertStats(seen=len(rows), changed=changed)
        logger.info(
            "Upserted batch %d: seen=%d changed=%d unchanged=%d",
            i // batch_size + 1,
            len(rows),
            changed,
            len(rows) - changed,
        )

        if (i // batch_size + 1) % 10 == 0:
            gc.collect()

    return totals
