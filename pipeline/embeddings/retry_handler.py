"""Retry queue handling for failed embeddings."""

from __future__ import annotations

import asyncio
import random
import logging
from typing import TYPE_CHECKING
from uuid import UUID


from pipeline.embeddings.batch_processor import (
    _classify_error,
    _log_failed_job,
    _process_with_semaphore,
)
from pipeline.models import Job

if TYPE_CHECKING:
    from pipeline.embedding import QueryEmbeddingService as EmbeddingService
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

MAX_RETRY_ATTEMPTS = 2


async def _process_retry_queue(
    retry_queue: list[tuple[UUID, str, str, int]],
    embedder: EmbeddingService,
    db: AsyncSession,
    semaphore: asyncio.Semaphore,
    batch_size: int,
    parallel_batches: int = 2,
) -> tuple[int, int, int, list[tuple[UUID, str, str, int]]]:
    """Process all retry attempts for failed jobs.

    Args:
        retry_queue: List of (job_id, error, retry_attempt) tuples
        embedder: Embedding service instance
        db: Database session for fetching jobs
        semaphore: Semaphore for concurrency control
        batch_size: Number of jobs per batch
        parallel_batches: Reserved for retry parallelism tuning

    Returns:
        Tuple of (success_count, error_count, skipped_count, remaining_queue)
    """
    total_success, total_errors, total_skipped = 0, 0, 0

    for retry_attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
        if not retry_queue:
            break

        logger.info(f"Retry attempt {retry_attempt}: {len(retry_queue)} failed jobs to retry")

        backoff_delay = (2**retry_attempt) + random.uniform(0, 0.5)
        logger.info(f"Waiting {backoff_delay}s before retry...")
        await asyncio.sleep(backoff_delay)

        job_ids_to_retry = [item[0] for item in retry_queue]
        retry_queue = []

        batch_num = 0
        for i in range(0, len(job_ids_to_retry), batch_size):
            batch_num += 1
            batch_job_ids = job_ids_to_retry[i : i + batch_size]

            try:
                result = await _process_with_semaphore(
                    semaphore, batch_job_ids, embedder, batch_num, retry_attempt=retry_attempt
                )
                success, errors, skipped, failed = result
                total_success += success
                total_errors += errors
                total_skipped += skipped

                retry_queue = _collect_retry_items(failed, retry_queue, retry_attempt)
            except asyncio.CancelledError:
                logger.warning(f"Retry batch {batch_num} cancelled")
                raise

    return total_success, total_errors, total_skipped, retry_queue


def _collect_retry_items(
    failed: list[tuple[Job, BaseException]],
    retry_queue: list[tuple[UUID, str, str, int]],
    retry_attempt: int,
) -> list[tuple[UUID, str, str, int]]:
    """Collect failed jobs for retry or log as permanently failed."""
    for job, error in failed:
        error_type, _ = _classify_error(error)
        if retry_attempt < MAX_RETRY_ATTEMPTS:
            retry_queue.append((job.id, error_type, str(error), retry_attempt))
        else:
            _log_failed_job(job, error_type, str(error), will_retry=False, retry_attempt=retry_attempt)
    return retry_queue


async def _log_exhausted_retries(
    retry_queue: list[tuple[UUID, str, str, int]],
    db: AsyncSession,
) -> int:
    """Log jobs that exhausted all retry attempts.

    Args:
        retry_queue: Remaining failed jobs
        db: Database session

    Returns:
        Count of exhausted jobs
    """
    if not retry_queue:
        return 0

    logger.warning(f"{len(retry_queue)} jobs exhausted retries, logging as failed")

    from pipeline.embeddings.batch_processor import _fetch_jobs_by_ids

    exhausted_job_ids = [item[0] for item in retry_queue]
    exhausted_jobs = await _fetch_jobs_by_ids(db, exhausted_job_ids)
    job_id_to_job = {job.id: job for job in exhausted_jobs}

    error_count = 0
    for job_id, error_type, error_msg, attempts in retry_queue:
        job = job_id_to_job.get(job_id)
        if job:
            _log_failed_job(job, error_type, error_msg, will_retry=False, retry_attempt=attempts)
        error_count += 1

    return error_count
