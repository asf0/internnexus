"""Classification step orchestration logic."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pipeline.classification import JobClassifier
from pipeline.models import Job
from sqlalchemy import func, select, update
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
    attempted_job_ids: set[object] = set()
    success = 0
    errors = 0

    while processed < total_jobs:
        batch_limit = min(commit_batch_size, total_jobs - processed)
        batch_query = (
            select(Job.id, Job.title, Job.description_text)
            .where(Job.job_category.is_(None))
            .order_by(
                Job.posted_at.desc().nulls_last(),
                Job.id.desc(),
            )
            .limit(batch_limit)
        )
        if attempted_job_ids:
            batch_query = batch_query.where(Job.id.notin_(attempted_job_ids))
        batch_result = await db.execute(batch_query)
        rows = batch_result.all()
        if not rows:
            logger.warning(
                "Classification stopped early at %d/%d jobs; no uncategorized rows returned after excluding %d attempted rows",
                processed,
                total_jobs,
                len(attempted_job_ids),
            )
            break

        inputs = [(row.title, row.description_text or "") for row in rows]
        categories_with_reason = await classifier.classify_batch_with_reasons(inputs)

        batch_success = 0
        batch_errors = 0
        failed_entries: list[tuple[object | None, str]] = []
        for row, (category, reason) in zip(rows, categories_with_reason):
            if category:
                await db.execute(update(Job).where(Job.id == row.id).values(job_category=category))
                success += 1
                batch_success += 1
            else:
                if row.id is not None:
                    attempted_job_ids.add(row.id)
                    failed_entries.append((row.id, reason))
                errors += 1
                batch_errors += 1

        if failed_entries:
            sample = ", ".join(f"{job_id}:{reason}" for job_id, reason in failed_entries[:10])
            logger.warning(
                "Classification failed for %d jobs in batch (sample: %s)",
                len(failed_entries),
                sample,
            )

        await db.commit()
        db.expunge_all()
        processed += len(rows)
        batch_success_rate = (batch_success / len(rows)) * 100 if rows else 0.0
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

    return ClassifyStepResult(success_count=success, error_count=errors, processed_count=processed)
