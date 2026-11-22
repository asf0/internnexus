"""Classification step orchestration logic."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import cast as type_cast
from uuid import UUID

from pipeline.stages.classification import JobClassifier
from pipeline.infra.models import Job
from pipeline.infra.job_cache import invalidate_job_detail_cache
from sqlalchemy import String, and_, cast, column, func, or_, select, update, values
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ClassifyStepResult:
    """Result of a classification step.

    Attributes:
        success_count: Number of jobs successfully classified.
        error_count: Number of jobs that failed classification.
        processed_count: Total number of jobs processed.
    """

    success_count: int
    error_count: int
    processed_count: int


def _batch_query(batch_limit: int, cursor_posted_at: datetime | None, cursor_id: object | None):
    query = (
        select(Job.id, Job.title, Job.description_text, Job.posted_at)
        .where(Job.job_category.is_(None))
        .order_by(Job.posted_at.desc().nulls_last(), Job.id.desc())
        .limit(batch_limit)
    )
    if cursor_id is None:
        return query
    if cursor_posted_at is None:
        return query.where(and_(Job.posted_at.is_(None), Job.id < cursor_id))
    return query.where(
        or_(
            Job.posted_at < cursor_posted_at,
            and_(
                Job.posted_at == cursor_posted_at,
                Job.id < cursor_id,
            ),
            Job.posted_at.is_(None),
        )
    )


async def _apply_batch_classifications(
    db: AsyncSession, rows, categories_with_reason
) -> tuple[int, int, list[tuple[object | None, str]], list[UUID]]:
    batch_success = 0
    batch_errors = 0
    failed_entries: list[tuple[object | None, str]] = []
    assignments: list[tuple[UUID, str]] = []
    for row, (category, reason) in zip(rows, categories_with_reason):
        if category:
            assignments.append((type_cast(UUID, row.id), category))
            batch_success += 1
        else:
            if row.id is not None:
                failed_entries.append((row.id, reason))
            batch_errors += 1

    if assignments:
        # One multi-row UPDATE instead of one round trip per job (202,654 in the
        # last measured window). The IS DISTINCT FROM guard matters more than the
        # batching: re-running classification previously rewrote every row even
        # when the category was unchanged, costing a row version and an
        # idx_jobs_category update for nothing.
        batch = values(
            column("id", PG_UUID(as_uuid=True)),
            column("category", String),
            name="v",
        ).data(assignments)
        await db.execute(
            update(Job)
            .where(Job.id == batch.c.id)
            .where(Job.job_category.is_distinct_from(batch.c.category))
            .values(job_category=cast(batch.c.category, String))
            .execution_options(synchronize_session=False)
        )

    return batch_success, batch_errors, failed_entries, [job_id for job_id, _ in assignments]


def _log_batch_failures(failed_entries: list[tuple[object | None, str]]) -> None:
    if not failed_entries:
        return
    sample = ", ".join(f"{job_id}:{reason}" for job_id, reason in failed_entries[:10])
    logger.warning(
        "Classification failed for %d jobs in batch (sample: %s)",
        len(failed_entries),
        sample,
    )


def _log_commit_progress(
    *,
    processed: int,
    total_jobs: int,
    batch_size: int,
    batch_success: int,
    batch_errors: int,
    success: int,
    errors: int,
) -> None:
    batch_success_rate = (batch_success / batch_size) * 100 if batch_size else 0.0
    cumulative_success_rate = (success / processed) * 100 if processed else 0.0
    logger.info(
        (
            "Classification commit progress: %d/%d "
            "(batch_success=%d, batch_errors=%d, batch_success_rate=%.1f%%; "
            "success=%d, errors=%d, cumulative_success_rate=%.1f%%)"
        ),
        processed,
        total_jobs,
        batch_success,
        batch_errors,
        batch_success_rate,
        success,
        errors,
        cumulative_success_rate,
    )


async def run_classify_step(
    *,
    db: AsyncSession,
    classifier: JobClassifier,
    commit_batch_size: int,
    limit: int | None = None,
) -> ClassifyStepResult:
    """Fetch uncategorized jobs, classify them in batches, and persist updates."""
    total_query = select(func.count()).select_from(Job).where(Job.job_category.is_(None))
    total_result = await db.execute(total_query)
    total_available = int(total_result.scalar() or 0)
    total_jobs = min(limit, total_available) if limit else total_available

    if total_jobs == 0:
        logger.info("No jobs to classify")
        return ClassifyStepResult(success_count=0, error_count=0, processed_count=0)

    logger.info("Classifying %d jobs without categories...", total_jobs)

    processed = 0
    cursor_posted_at: datetime | None = None
    cursor_id: object | None = None
    success = 0
    errors = 0

    while processed < total_jobs:
        batch_limit = min(commit_batch_size, total_jobs - processed)
        batch_result = await db.execute(_batch_query(batch_limit, cursor_posted_at, cursor_id))
        rows = batch_result.all()
        if not rows:
            logger.warning(
                "Classification stopped early at %d/%d jobs; no more uncategorized rows after cursor %s",
                processed,
                total_jobs,
                cursor_id,
            )
            break

        inputs = [(row.title, row.description_text or "") for row in rows]
        categories_with_reason = await classifier.classify_batch_with_reasons(inputs)

        batch_success, batch_errors, failed_entries, changed_ids = await _apply_batch_classifications(
            db, rows, categories_with_reason
        )
        success += batch_success
        errors += batch_errors
        _log_batch_failures(failed_entries)

        await db.commit()
        await invalidate_job_detail_cache(changed_ids)
        db.expunge_all()
        raw_posted_at = getattr(rows[-1], "posted_at", None)
        cursor_posted_at = raw_posted_at if isinstance(raw_posted_at, datetime) else None
        cursor_id = rows[-1].id
        processed += len(rows)
        _log_commit_progress(
            processed=processed,
            total_jobs=total_jobs,
            batch_size=len(rows),
            batch_success=batch_success,
            batch_errors=batch_errors,
            success=success,
            errors=errors,
        )

    return ClassifyStepResult(success_count=success, error_count=errors, processed_count=processed)
