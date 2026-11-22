"""Retry queue handling for failed embeddings."""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING
from uuid import UUID

from pipeline.infra.async_retry import RetryPolicy, delay_for_attempt
from pipeline.stages.embeddings.batch_records import RetryItem, classify_failures
from pipeline.stages.embeddings.batch_embedder import (
    _fetch_jobs_by_ids,
    _log_failed_job,
    _process_with_semaphore,
)

if TYPE_CHECKING:
    from pipeline.infra.embedding import QueryEmbeddingService as EmbeddingService
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

MAX_RETRY_ATTEMPTS = 2
_EMBEDDING_RETRY_POLICY = RetryPolicy(
    max_attempts=MAX_RETRY_ATTEMPTS,
    base_delay=2,
    max_delay=4,
    jitter_max=0.5,
)


def _provider_retry_after(retry_queue: list[tuple[UUID, str, str, int]]) -> float | None:
    delays = []
    for _, _, message, _ in retry_queue:
        match = re.search(r"Retry-After:\s*(\d+(?:\.\d+)?)", message, re.IGNORECASE)
        if match:
            delays.append(float(match.group(1)))
    return max(delays) if delays else None


def _retry_delay(
    retry_queue: list[tuple[UUID, str, str, int]],
    retry_attempt: int,
    random_value: Callable[[], float] | None,
) -> float:
    delay_options = {}
    provider_delay = _provider_retry_after(retry_queue)
    if provider_delay is not None:
        delay_options["provider_retry_after"] = provider_delay
    if random_value is not None:
        delay_options["random_value"] = random_value
    return delay_for_attempt(
        _EMBEDDING_RETRY_POLICY,
        retry_attempt,
        **delay_options,
    )


async def _process_retry_queue(
    retry_queue: list[tuple[UUID, str, str, int]],
    embedder: EmbeddingService,
    db: AsyncSession,
    semaphore: asyncio.Semaphore,
    batch_size: int,
    parallel_batches: int = 2,
    sleep: Callable[[float], Awaitable[None]] | None = None,
    random_value: Callable[[], float] | None = None,
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
    del db, parallel_batches
    total_success, total_errors, total_skipped = 0, 0, 0
    permanent_failed_ids: set[UUID] = set()

    for retry_attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
        if not retry_queue:
            break

        logger.info(f"Retry attempt {retry_attempt}: {len(retry_queue)} failed jobs to retry")

        backoff_delay = _retry_delay(retry_queue, retry_attempt, random_value)
        logger.info(f"Waiting {backoff_delay}s before retry...")
        await (sleep or asyncio.sleep)(backoff_delay)

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
                total_skipped += skipped

                retryable_items, permanent = classify_failures(failed)
                permanent_failed_ids |= permanent
                retryable_failed = len(retryable_items)
                total_errors = len(permanent_failed_ids) + max(
                    0,
                    total_errors - len(permanent_failed_ids) + errors - retryable_failed,
                )

                retry_queue = [
                    RetryItem(job_id, error_type, message, retry_attempt)
                    for job_id, error_type, message in retryable_items
                ]
            except asyncio.CancelledError:
                logger.warning(f"Retry batch {batch_num} cancelled")
                raise

    return total_success, total_errors, total_skipped, retry_queue


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

    exhausted_job_ids = [item[0] for item in retry_queue]
    exhausted_jobs = await _fetch_jobs_by_ids(db, exhausted_job_ids)
    job_id_to_job = {job.id: job for job in exhausted_jobs}

    error_count = 0
    for job_id, error_type, error_msg, attempts in retry_queue:
        job = job_id_to_job.get(job_id)
        if job:
            _log_failed_job(
                job.id,
                error_type,
                error_msg,
                will_retry=False,
                retry_attempt=attempts,
                company=job.company,
                title=job.title,
            )
        error_count += 1

    return error_count
