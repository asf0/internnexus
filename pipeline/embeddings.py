"""Embeddings generation module - create vector embeddings for job matching."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# Import from backend app (requires project root in PYTHONPATH)
from app.db import AsyncSessionLocal
from app.models import Job
from app.services.embedding_service import EmbeddingError, EmbeddingService, RateLimitError
from app.utils.text import clean_text_for_embedding

logger = logging.getLogger(__name__)

LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

PARALLEL_BATCHES = 1
EMBEDDING_BATCH_SIZE = 10
MAX_RETRY_ATTEMPTS = 2
MAX_EMPTY_BATCHES = 3


def _get_skipped_jobs_log_path() -> Path:
    """Get today's log file path for skipped jobs."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return LOGS_DIR / f"skipped_jobs_{today}.jsonl"


def _get_failed_jobs_log_path() -> Path:
    """Get today's log file path for failed jobs."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return LOGS_DIR / f"failed_jobs_{today}.jsonl"


def _rotate_old_logs() -> None:
    """Delete log files older than 7 days."""
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        for log_file in LOGS_DIR.glob("skipped_jobs_*.jsonl"):
            try:
                date_str = log_file.stem.split("_")[-1]
                file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if file_date < cutoff:
                    log_file.unlink()
                    logger.debug(f"Rotated old log: {log_file.name}")
            except (ValueError, OSError):
                continue
        for log_file in LOGS_DIR.glob("failed_jobs_*.jsonl"):
            try:
                date_str = log_file.stem.split("_")[-1]
                file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if file_date < cutoff:
                    log_file.unlink()
                    logger.debug(f"Rotated old log: {log_file.name}")
            except (ValueError, OSError):
                continue
    except Exception as e:
        logger.debug(f"Log rotation error: {e}")


def _log_skipped_job(job: Job, reason: str, text_length: int) -> None:
    """Log a skipped job to the daily log file."""
    try:
        _rotate_old_logs()
        log_path = _get_skipped_jobs_log_path()

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "job_id": str(job.id),
            "company": job.company,
            "title": job.title,
            "apply_url": job.apply_url,
            "reason": reason,
            "text_length": text_length,
        }

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.debug(f"Failed to log skipped job: {e}")


def _log_failed_job(
    job: Job,
    error_type: str,
    error_message: str,
    will_retry: bool,
    retry_attempt: int = 0,
) -> None:
    """Log a failed job to the daily log file."""
    try:
        _rotate_old_logs()
        log_path = _get_failed_jobs_log_path()

        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "job_id": str(job.id),
            "company": job.company,
            "title": job.title,
            "apply_url": job.apply_url,
            "error_type": error_type,
            "error_message": error_message[:500] if error_message else "",
            "will_retry": will_retry,
        }
        if retry_attempt > 0:
            entry["retry_attempt"] = retry_attempt

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.debug(f"Failed to log failed job: {e}")


def _classify_error(error: BaseException) -> tuple[str, bool]:
    """Classify error as (error_type, is_retryable).

    Returns:
        Tuple of (error_type_string, is_retryable_boolean)
    """
    if isinstance(error, RateLimitError):
        return "rate_limit", True
    if isinstance(error, EmbeddingError):
        return "embedding_error", error.retryable
    if isinstance(error, asyncio.TimeoutError):
        return "timeout", True
    if isinstance(error, asyncio.CancelledError):
        return "cancelled", False
    return "unknown", True


async def _fetch_jobs_batch(db: AsyncSession, batch_size: int) -> list[Job]:
    """Fetch a batch of jobs without embeddings using SKIP LOCKED.

    Uses FOR UPDATE SKIP LOCKED to prevent race conditions when multiple
    parallel batches are fetching jobs simultaneously.

    Filters out jobs with empty/short description_text (< 30 chars after
    stripping HTML) since they cannot be meaningfully embedded.

    Args:
        db: Database session to use
        batch_size: Maximum number of jobs to fetch

    Returns:
        List of jobs needing embeddings
    """
    job_ids = await _fetch_job_ids_batch(db, batch_size)
    if not job_ids:
        return []
    result = await db.execute(select(Job).where(Job.id.in_(job_ids)))
    jobs = result.scalars().all()
    return list(jobs)


async def _fetch_job_ids_batch(db: AsyncSession, batch_size: int) -> list[int]:
    """Fetch a batch of job IDs without embeddings.

    Returns just IDs so that parallel tasks can fetch their own Job objects
    in their own sessions. Note: Does NOT use FOR UPDATE locking since the
    main session would hold locks that block the parallel worker sessions.
    Parallel workers handle their own locking via _fetch_jobs_by_ids().

    Filters out jobs with empty/short description_text (< 30 chars after
    stripping HTML) since they cannot be meaningfully embedded.

    Args:
        db: Database session to use
        batch_size: Maximum number of job IDs to fetch

    Returns:
        List of job IDs needing embeddings
    """
    cleaned_text = func.regexp_replace(
        func.regexp_replace(
            func.regexp_replace(Job.description_text, r"<[^>]+>", " ", "g"),
            r"&[a-zA-Z]+;",
            " ",
            "g",
        ),
        r"\s+",
        " ",
        "g",
    )
    result = await db.execute(
        select(Job.id)
        .where(Job.description_embedding.is_(None))
        .where(func.length(func.trim(cleaned_text)) >= 30)
        .order_by(Job.id)
        .limit(batch_size)
    )
    job_ids = result.scalars().all()
    return list(job_ids)


async def _get_remaining_count(db: AsyncSession) -> int:
    """Get the current count of jobs without embeddings that have sufficient description text.

    Uses the same HTML-stripping logic as the fetch query to ensure accurate count.

    Args:
        db: Database session to use

    Returns:
        Count of jobs needing embeddings
    """
    cleaned_text = func.regexp_replace(
        func.regexp_replace(
            func.regexp_replace(Job.description_text, r"<[^>]+>", " ", "g"),
            r"&[a-zA-Z]+;",
            " ",
            "g",
        ),
        r"\s+",
        " ",
        "g",
    )
    result = await db.execute(
        select(func.count())
        .select_from(Job)
        .where(Job.description_embedding.is_(None))
        .where(func.length(func.trim(cleaned_text)) >= 30)
    )
    return result.scalar() or 0


async def _fetch_jobs_by_ids(db: AsyncSession, job_ids: list[int]) -> list[Job]:
    """Fetch specific jobs by ID for retry.

    Args:
        db: Database session to use
        job_ids: List of job IDs to fetch

    Returns:
        List of jobs matching the IDs
    """
    if not job_ids:
        return []
    result = await db.execute(select(Job).where(Job.id.in_(job_ids)))
    jobs = result.scalars().all()
    return list(jobs)


async def _process_batch(
    db: AsyncSession,
    jobs: list[Job],
    embedder: EmbeddingService,
    batch_num: int,
    retry_attempt: int = 0,
) -> tuple[int, int, int, list[tuple[Job, BaseException]]]:
    """Process a single batch of jobs with embeddings.

    Args:
        db: Database session to use
        jobs: List of jobs to process
        embedder: Embedding service instance
        batch_num: Batch number for logging
        retry_attempt: Current retry attempt (0 = initial)

    Returns:
        Tuple of (success_count, error_count, skipped_count, failed_jobs_for_retry)
    """
    if not jobs:
        return 0, 0, 0, []

    jobs_in_db = []
    texts = []

    for job in jobs:
        desc_raw = getattr(job, "description_text", None)
        desc_str = str(desc_raw) if desc_raw is not None else ""
        text = clean_text_for_embedding(desc_str)
        text_length = len(text)

        if not text:
            _log_skipped_job(job, "empty_text", text_length)
            continue
        if text_length < 30:
            _log_skipped_job(job, "too_short", text_length)
            continue

        jobs_in_db.append(job)
        texts.append(text)

    skipped = len(jobs) - len(jobs_in_db)

    if not jobs_in_db:
        return 0, 0, skipped, []

    success = 0
    errors = 0
    failed_for_retry: list[tuple[Job, BaseException]] = []

    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch_texts = texts[i : i + EMBEDDING_BATCH_SIZE]
        batch_jobs = jobs_in_db[i : i + EMBEDDING_BATCH_SIZE]

        try:
            embeddings = await embedder.embed_many(batch_texts, batch_size=EMBEDDING_BATCH_SIZE)
            for job, embedding in zip(batch_jobs, embeddings):
                job.description_embedding = embedding
                db.add(job)
                success += 1
        except asyncio.CancelledError:
            logger.warning(f"  Batch {batch_num} cancelled during embedding")
            raise
        except EmbeddingError as e:
            error_type, is_retryable = _classify_error(e)

            if is_retryable:
                for job in batch_jobs:
                    failed_for_retry.append((job, e))
                logger.warning(
                    f"  Batch {batch_num} sub-batch error (retryable): {error_type} - {e}"
                )
            else:
                for job in batch_jobs:
                    _log_failed_job(
                        job, error_type, str(e), will_retry=False, retry_attempt=retry_attempt
                    )
                errors += len(batch_jobs)
                logger.warning(
                    f"  Batch {batch_num} sub-batch error (permanent): {error_type} - {e}"
                )
        except Exception as e:
            error_type, is_retryable = _classify_error(e)

            if is_retryable:
                for job in batch_jobs:
                    failed_for_retry.append((job, e))
                logger.warning(
                    f"  Batch {batch_num} sub-batch error (retryable, unknown): {type(e).__name__} - {e}"
                )
            else:
                for job in batch_jobs:
                    _log_failed_job(
                        job, error_type, str(e), will_retry=False, retry_attempt=retry_attempt
                    )
                errors += len(batch_jobs)

    await db.commit()
    return success, errors, skipped, failed_for_retry


async def _process_with_semaphore(
    semaphore: asyncio.Semaphore,
    job_ids: list[int],
    embedder: EmbeddingService,
    batch_num: int,
    retry_attempt: int = 0,
) -> tuple[int, int, int, list[tuple[Job, BaseException]]]:
    """Process a batch with semaphore-controlled concurrency.

    Each batch gets its own database session to allow parallel processing.
    Job IDs are passed in and fresh Job objects are fetched within the new session
    to avoid SQLAlchemy session attachment conflicts.

    Args:
        semaphore: Semaphore to control concurrency
        job_ids: List of job IDs to process
        embedder: Embedding service instance
        batch_num: Batch number for logging
        retry_attempt: Current retry attempt

    Returns:
        Tuple of (success_count, error_count, skipped_count, failed_jobs)
    """
    async with semaphore:
        async with AsyncSessionLocal() as db:
            # Fetch fresh Job objects within this session to avoid session conflicts
            jobs = await _fetch_jobs_by_ids(db, job_ids)
            result = await _process_batch(
                db, jobs, embedder, batch_num, retry_attempt=retry_attempt
            )
            success, errors, skipped, failed = result
            logger.info(
                f"  Batch {batch_num}: {success} success, {errors} errors, {skipped} skipped"
                + (f" (retry {retry_attempt})" if retry_attempt > 0 else "")
            )
            return result


async def generate_embeddings(
    session: AsyncSession | None = None, batch_size: int = 50
) -> tuple[int, int]:
    """Generate embeddings for jobs without them using parallel processing.

    Uses a single database session for sequential operations (counting, logging)
    and separate sessions for parallel batch processing.

    Args:
        session: Optional existing session (unused, kept for API compatibility)
        batch_size: Number of jobs to process per parallel batch

    Returns:
        Tuple of (success_count, error_count)
    """
    logger.info("=" * 60)
    logger.info("STEP 4: Generating embeddings (parallel mode with retry)...")
    logger.info("=" * 60)

    total_success, total_errors, total_skipped = 0, 0, 0
    retry_queue: list[tuple[int, BaseException, int]] = []  # (job_id, error, retry_attempt)
    cancelled = False

    try:
        embedder = EmbeddingService()
        logger.info(f"Using embedding provider: {embedder._provider}, model: {embedder._model}")
    except Exception as e:
        logger.error(f"Failed to initialize embedding service: {e}")
        return 0, 0

    # Use a single session for sequential operations
    async with AsyncSessionLocal() as db:
        initial_count = await _get_remaining_count(db)
        logger.info(f"Found {initial_count} jobs without embeddings")

        if initial_count == 0:
            logger.info("No jobs need embeddings")
            return 0, 0

        semaphore = asyncio.Semaphore(PARALLEL_BATCHES)
        batch_num = 0
        consecutive_empty = 0

        try:
            while True:
                pending_batches = []

                for _ in range(PARALLEL_BATCHES):
                    batch_num += 1
                    # Fetch just the IDs to avoid session attachment issues
                    job_ids = await _fetch_job_ids_batch(db, batch_size)

                    if not job_ids:
                        consecutive_empty += 1
                        if consecutive_empty >= MAX_EMPTY_BATCHES:
                            logger.info(f"No more jobs to process (empty batches)")
                            break
                        continue

                    consecutive_empty = 0
                    pending_batches.append(
                        _process_with_semaphore(semaphore, job_ids, embedder, batch_num)
                    )

                if not pending_batches:
                    break

                results = await asyncio.gather(*pending_batches, return_exceptions=True)

                for result in results:
                    if isinstance(result, BaseException):
                        if isinstance(result, asyncio.CancelledError):
                            cancelled = True
                            continue
                        logger.error(f"Batch failed with exception: {result}")
                        total_errors += batch_size
                    else:
                        success, errors, skipped, failed = result
                        total_success += success
                        total_errors += errors
                        total_skipped += skipped
                        for job, error in failed:
                            retry_queue.append((job.id, error, 0))

                if cancelled:
                    break

                remaining = await _get_remaining_count(db)
                logger.info(
                    f"Progress: {total_success} embedded, {total_errors} errors, "
                    f"{total_skipped} skipped, {remaining} remaining"
                )

            if not cancelled and retry_queue:
                for retry_attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
                    if not retry_queue:
                        break

                    logger.info(
                        f"Retry attempt {retry_attempt}: {len(retry_queue)} failed jobs to retry"
                    )

                    backoff_delay = 2**retry_attempt
                    logger.info(f"Waiting {backoff_delay}s before retry...")
                    await asyncio.sleep(backoff_delay)

                    job_ids_to_retry = [item[0] for item in retry_queue]
                    retry_queue = []

                    batch_num = 0
                    for i in range(0, len(job_ids_to_retry), batch_size):
                        batch_num += 1
                        batch_job_ids = job_ids_to_retry[i : i + batch_size]

                        try:
                            success, errors, skipped, failed = await _process_with_semaphore(
                                semaphore,
                                batch_job_ids,
                                embedder,
                                batch_num,
                                retry_attempt=retry_attempt,
                            )
                            total_success += success
                            total_errors += errors
                            total_skipped += skipped
                            for job, error in failed:
                                if retry_attempt < MAX_RETRY_ATTEMPTS:
                                    retry_queue.append((job.id, error, retry_attempt))
                                else:
                                    error_type, _ = _classify_error(error)
                                    _log_failed_job(
                                        job,
                                        error_type,
                                        str(error),
                                        will_retry=False,
                                        retry_attempt=retry_attempt,
                                    )
                                    total_errors += 1
                        except asyncio.CancelledError:
                            logger.warning(f"Retry batch {batch_num} cancelled")
                            cancelled = True
                            break

                    if cancelled:
                        break

            if retry_queue:
                logger.warning(f"{len(retry_queue)} jobs exhausted retries, logging as failed")
                # Fetch jobs for logging (they have Job details like company, title, etc.)
                exhausted_job_ids = [item[0] for item in retry_queue]
                exhausted_jobs = await _fetch_jobs_by_ids(db, exhausted_job_ids)
                job_id_to_job = {job.id: job for job in exhausted_jobs}
                for job_id, error, attempts in retry_queue:
                    error_type, _ = _classify_error(error)
                    job = job_id_to_job.get(job_id)
                    if job:
                        _log_failed_job(
                            job, error_type, str(error), will_retry=False, retry_attempt=attempts
                        )
                    total_errors += 1

        except asyncio.CancelledError:
            logger.warning("Embedding generation cancelled. Saving progress...")
            cancelled = True

        if cancelled and retry_queue:
            # Fetch jobs for logging cancelled retries
            cancelled_job_ids = [item[0] for item in retry_queue]
            cancelled_jobs = await _fetch_jobs_by_ids(db, cancelled_job_ids)
            job_id_to_job = {job.id: job for job in cancelled_jobs}
            for job_id, error, attempts in retry_queue:
                error_type, _ = _classify_error(error)
                job = job_id_to_job.get(job_id)
                if job:
                    _log_failed_job(
                        job, error_type, str(error), will_retry=False, retry_attempt=attempts
                    )

        final_remaining = await _get_remaining_count(db)
        logger.info(
            f"Embedding complete: {total_success} success, {total_errors} errors, "
            f"{total_skipped} skipped, {final_remaining} still remaining"
        )

    if total_errors > 0:
        failed_log = _get_failed_jobs_log_path()
        logger.info(f"Failed jobs logged to: {failed_log}")

    return total_success, total_errors
