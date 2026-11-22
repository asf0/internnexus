"""Job-row preparation and changed-only upsert statement construction.

These builders live in the repository layer so both the ingestion stage and
board-snapshot reconciliation can share them without importing upward.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import case, or_
from sqlalchemy.dialects.postgresql import insert

from internnexus_core.text import clean_job_description, embedding_input_hash, strip_control_chars
from pipeline.domain.job_identity import fingerprint_for
from pipeline.domain.schemas import JobSchema
from pipeline.infra.models import Job, JobSource


def build_job_rows(jobs: list[JobSchema]) -> tuple[list[dict], list[dict]]:
    """Project jobs into job and sighting insert rows."""
    job_rows: list[dict] = []
    sighting_rows: list[dict] = []
    for job in jobs:
        fingerprint = fingerprint_for(job)
        source = JobSource(job.source)
        description_text = clean_job_description(job.description_text) or ""
        job_rows.append(
            {
                "fingerprint": fingerprint,
                "source": source,
                "title": strip_control_chars(job.title) or "",
                "company": strip_control_chars(job.company) or "",
                "location": strip_control_chars(job.location),
                "apply_url": strip_control_chars(job.apply_url) or "",
                "description_text": description_text,
                "description_embedding": job.description_embedding,
                "embedding_input_hash": embedding_input_hash(description_text),
                "job_category": job.job_category,
                "job_type": job.job_type,
                "work_mode": job.work_mode,
                "posted_at": job.posted_at,
                "is_active": True,
            }
        )
        sighting_rows.append({"fingerprint": fingerprint, "source": source})
    return job_rows, sighting_rows


def changed_only_job_upsert(rows: list[dict]):
    """Build the insert-on-conflict statement that only writes changed rows."""
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
    # Legacy rows have no hash. Until they are touched by a material source
    # update, use the old description comparison as a conservative fallback.
    embedding_input_changed = or_(
        Job.embedding_input_hash.is_not(None)
        & Job.embedding_input_hash.is_distinct_from(excluded.embedding_input_hash),
        Job.embedding_input_hash.is_(None) & description_changed,
    )

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
            "embedding_input_hash": excluded.embedding_input_hash,
            "description_embedding": case(
                (embedding_input_changed, None),
                else_=Job.description_embedding,
            ),
            "embedding_skip_reason": case(
                (embedding_input_changed, None),
                else_=Job.embedding_skip_reason,
            ),
            "embedding_skipped_at": case(
                (embedding_input_changed, None),
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
