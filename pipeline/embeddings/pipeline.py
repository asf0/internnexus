"""Main orchestration for embedding generation pipeline."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from pipeline.backend_bridge import EmbeddingService
from pipeline.repositories.sqlalchemy_repo import AsyncSessionLocal

from pipeline.embeddings.batch_processor import (
    _fetch_job_ids_batch,
    _get_failed_jobs_log_path,
    _get_remaining_count,
    _process_with_semaphore,
)
from pipeline.embeddings.retry_handler import (
    _log_exhausted_retries,
    _process_retry_queue,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

PARALLEL_BATCHES = 2
MAX_EMPTY_BATCHES = 3
PROGRESS_LOG_EVERY_BATCHES = 5


async def generate_embeddings(
    session: AsyncSession | None = None,
    batch_size: int = 50,
    parallel_batches: int = PARALLEL_BATCHES,
) -> tuple[int, int]:
    """Generate embeddings for jobs without them using parallel processing."""
    logger.info("=" * 60)
    logger.info("STEP 4: Generating embeddings (parallel mode with retry)...")
    logger.info("=" * 60)

    embedder = _initialize_embedder()
    if embedder is None:
        return 0, 0

    if session is not None:
        return await _run_embedding_pipeline(session, embedder, batch_size, parallel_batches)

    async with AsyncSessionLocal() as db:
        return await _run_embedding_pipeline(db, embedder, batch_size, parallel_batches)


def _initialize_embedder() -> EmbeddingService | None:
    """Initialize the embedding service."""
    try:
        embedder = EmbeddingService()
        logger.info(f"Using embedding provider: {embedder._provider}, model: {embedder._model}")
        return embedder
    except Exception as e:
        logger.error(f"Failed to initialize embedding service: {e}")
        return None


async def _run_embedding_pipeline(
    db: AsyncSession,
    embedder: EmbeddingService,
    batch_size: int,
    parallel_batches: int,
) -> tuple[int, int]:
    """Run the full embedding pipeline."""
    initial_count = await _get_remaining_count(db)
    logger.info(f"Found {initial_count} jobs without embeddings")

    if initial_count == 0:
        logger.info("No jobs need embeddings")
        return 0, 0

    effective_parallel_batches = max(1, parallel_batches)
    semaphore = asyncio.Semaphore(effective_parallel_batches)
    total_success, total_errors, total_skipped = 0, 0, 0
    retry_queue: list[tuple[int, BaseException, int]] = []

    try:
        result = await _process_batches(
            db,
            semaphore,
            embedder,
            batch_size,
            effective_parallel_batches,
        )
        total_success, total_errors, total_skipped, retry_queue, _ = result

        if retry_queue:
            total_success, total_errors, total_skipped = await _handle_retries(
                retry_queue,
                embedder,
                db,
                semaphore,
                batch_size,
                effective_parallel_batches,
                total_success,
                total_errors,
                total_skipped,
            )

    except asyncio.CancelledError:
        logger.warning("Embedding generation cancelled. Saving progress...")

    await _log_final_stats(db, total_success, total_errors, total_skipped)

    if total_errors > 0:
        logger.info(f"Failed jobs logged to: {_get_failed_jobs_log_path()}")

    return total_success, total_errors


async def _handle_retries(
    retry_queue: list[tuple[int, BaseException, int]],
    embedder: EmbeddingService,
    db: AsyncSession,
    semaphore: asyncio.Semaphore,
    batch_size: int,
    parallel_batches: int,
    total_success: int,
    total_errors: int,
    total_skipped: int,
) -> tuple[int, int, int]:
    """Handle retry queue processing."""
    retry_result = await _process_retry_queue(
        retry_queue,
        embedder,
        db,
        semaphore,
        batch_size,
        parallel_batches=parallel_batches,
    )
    retry_success, retry_errors, retry_skipped, retry_queue = retry_result
    total_success += retry_success
    total_errors += retry_errors
    total_skipped += retry_skipped

    if retry_queue:
        exhausted_errors = await _log_exhausted_retries(retry_queue, db)
        total_errors += exhausted_errors

    return total_success, total_errors, total_skipped


async def _process_batches(
    db: AsyncSession,
    semaphore: asyncio.Semaphore,
    embedder: EmbeddingService,
    batch_size: int,
    parallel_batches: int,
) -> tuple[int, int, int, list[tuple[int, BaseException, int]], bool]:
    """Process all batches of jobs."""
    total_success, total_errors, total_skipped = 0, 0, 0
    retry_queue: list[tuple[int, BaseException, int]] = []
    cancelled = False
    batch_num = 0
    consecutive_empty = 0
    batches_since_progress_log = 0

    while True:
        (
            pending_batches,
            batch_num,
            consecutive_empty,
            should_break,
        ) = await _collect_pending_batches(
            db,
            semaphore,
            embedder,
            batch_size,
            batch_num,
            consecutive_empty,
            parallel_batches,
        )

        if should_break or not pending_batches:
            break

        results = await asyncio.gather(*pending_batches, return_exceptions=True)
        cancelled = _process_results(results, retry_queue, batch_size)

        if cancelled:
            break

        total_success, total_errors, total_skipped = _accumulate_results(
            results, total_success, total_errors, total_skipped, retry_queue, batch_size
        )
        batches_since_progress_log += len(pending_batches)
        if batches_since_progress_log >= PROGRESS_LOG_EVERY_BATCHES:
            await _log_progress(db, total_success, total_errors, total_skipped)
            batches_since_progress_log = 0

    return total_success, total_errors, total_skipped, retry_queue, cancelled


async def _collect_pending_batches(
    db: AsyncSession,
    semaphore: asyncio.Semaphore,
    embedder: EmbeddingService,
    batch_size: int,
    batch_num: int,
    consecutive_empty: int,
    parallel_batches: int,
) -> tuple[list, int, int, bool]:
    """Collect pending batches for processing."""
    pending_batches = []
    should_break = False

    for _ in range(max(1, parallel_batches)):
        batch_num += 1
        job_ids = await _fetch_job_ids_batch(db, batch_size)

        if not job_ids:
            consecutive_empty += 1
            if consecutive_empty >= MAX_EMPTY_BATCHES:
                logger.info("No more jobs to process (empty batches)")
                should_break = True
                break
            continue

        consecutive_empty = 0
        pending_batches.append(_process_with_semaphore(semaphore, job_ids, embedder, batch_num))

    return pending_batches, batch_num, consecutive_empty, should_break


def _process_results(
    results: list,
    retry_queue: list[tuple[int, BaseException, int]],
    batch_size: int,
) -> bool:
    """Process batch results and return if cancelled."""
    for result in results:
        if isinstance(result, asyncio.CancelledError):
            return True
        if isinstance(result, BaseException):
            logger.error(f"Batch failed with exception: {result}")
    return False


def _accumulate_results(
    results: list,
    total_success: int,
    total_errors: int,
    total_skipped: int,
    retry_queue: list[tuple[int, BaseException, int]],
    batch_size: int,
) -> tuple[int, int, int]:
    """Accumulate results from batch processing."""
    for result in results:
        if isinstance(result, BaseException):
            if not isinstance(result, asyncio.CancelledError):
                total_errors += batch_size
        else:
            success, errors, skipped, failed = result
            total_success += success
            total_errors += errors
            total_skipped += skipped
            for job, error in failed:
                retry_queue.append((job.id, error, 0))
    return total_success, total_errors, total_skipped


async def _log_progress(
    db: AsyncSession, total_success: int, total_errors: int, total_skipped: int
) -> None:
    """Log current progress."""
    remaining = await _get_remaining_count(db)
    logger.info(
        f"Progress: {total_success} embedded, {total_errors} errors, "
        f"{total_skipped} skipped, {remaining} remaining"
    )


async def _log_final_stats(
    db: AsyncSession,
    total_success: int,
    total_errors: int,
    total_skipped: int,
) -> None:
    """Log final statistics."""
    final_remaining = await _get_remaining_count(db)
    logger.info(
        f"Embedding complete: {total_success} success, {total_errors} errors, "
        f"{total_skipped} skipped, {final_remaining} still remaining"
    )
