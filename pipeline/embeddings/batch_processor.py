"""Batch processing logic for embedding generation."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from pipeline.embedding import (
    EmbeddingError,
    QueryEmbeddingService as EmbeddingService,
    RateLimitError,
)
from pipeline.repositories.job_text_sql import embedding_candidate_text_sql
from pipeline.text import clean_text_for_embedding
from pipeline.runtime.config import get_config
from pipeline.repositories.sqlalchemy_repo import AsyncSessionLocal, Job

logger = logging.getLogger(__name__)

LOGS_DIR = Path(__file__).parent.parent.parent.parent / "logs"
EMBEDDING_BATCH_SIZE = 16  # default; get_config().embeddings.api_batch_size overrides at runtime
LOG_FLUSH_BATCH_SIZE = 100
MIN_EMBEDDABLE_TEXT_LENGTH = 30


def _embedding_candidate_text_sql():
    return embedding_candidate_text_sql()


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
        for pattern in ["skipped_jobs_*.jsonl", "failed_jobs_*.jsonl"]:
            _rotate_log_files(pattern, cutoff)
    except Exception as e:
        logger.debug(f"Log rotation error: {e}")


def _rotate_log_files(pattern: str, cutoff: datetime) -> None:
    """Rotate log files matching pattern older than cutoff."""
    for log_file in LOGS_DIR.glob(pattern):
        try:
            date_str = log_file.stem.split("_")[-1]
            file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if file_date < cutoff:
                log_file.unlink()
                logger.debug(f"Rotated old log: {log_file.name}")
        except (ValueError, OSError):
            pass


def _log_skipped_job(job: Job, reason: str, text_length: int) -> None:
    """Log a skipped job to the daily log file."""
    try:
        _rotate_old_logs()
        log_path = _get_skipped_jobs_log_path()
        LOGS_DIR.mkdir(exist_ok=True)

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


def _append_jsonl_batch(path: Path, entries: list[dict[str, Any]]) -> None:
    """Append multiple JSONL records in a single write."""
    if not entries:
        return
    try:
        _rotate_old_logs()
        LOGS_DIR.mkdir(exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.writelines(json.dumps(entry) + "\n" for entry in entries)
    except Exception as e:
        logger.debug(f"Failed to append JSONL batch: {e}")


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
        LOGS_DIR.mkdir(exist_ok=True)

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
    """Classify error as (error_type, is_retryable)."""
    if isinstance(error, RateLimitError):
        return "rate_limit", True
    if isinstance(error, EmbeddingError):
        return "embedding_error", error.retryable
    if isinstance(error, asyncio.TimeoutError):
        return "timeout", True
    if isinstance(error, asyncio.CancelledError):
        return "cancelled", False
    return "unknown", True


async def _fetch_job_ids_batch(
    db: AsyncSession,
    batch_size: int,
    excluded_ids: set[UUID] | None = None,
) -> list[UUID]:
    """Fetch a batch of job IDs without embeddings or permanent skip markers."""
    cleaned_text = embedding_candidate_text_sql()
    stmt = (
        select(Job.id)
        .where(Job.description_embedding.is_(None))
        .where(Job.embedding_skip_reason.is_(None))
        .where(func.length(cleaned_text) >= MIN_EMBEDDABLE_TEXT_LENGTH)
        .order_by(Job.id)
        .limit(batch_size)
    )
    if excluded_ids:
        stmt = stmt.where(Job.id.notin_(excluded_ids))

    result = await db.execute(stmt)
    job_ids = result.scalars().all()
    return list(job_ids)


async def _fetch_jobs_by_ids(db: AsyncSession, job_ids: list[UUID]) -> list[Job]:
    """Fetch specific jobs by ID for retry."""
    if not job_ids:
        return []
    result = await db.execute(select(Job).where(Job.id.in_(job_ids)).options(defer(Job.description_embedding)))
    jobs = result.scalars().all()
    return list(jobs)


async def _get_remaining_count(db: AsyncSession) -> int:
    """Get the current count of jobs without embeddings."""
    cleaned_text = embedding_candidate_text_sql()
    result = await db.execute(
        select(func.count())
        .select_from(Job)
        .where(Job.description_embedding.is_(None))
        .where(Job.embedding_skip_reason.is_(None))
        .where(func.length(cleaned_text) >= MIN_EMBEDDABLE_TEXT_LENGTH)
    )
    return result.scalar() or 0


async def _process_batch(
    db: AsyncSession,
    jobs: list[Job],
    embedder: EmbeddingService,
    batch_num: int,
    retry_attempt: int = 0,
) -> tuple[int, int, int, list[tuple[Job, BaseException]]]:
    """Process a single batch of jobs with embeddings."""
    if not jobs:
        return 0, 0, 0, []

    jobs_in_db, texts, skipped_jobs = _prepare_job_texts(jobs)
    skipped = len(skipped_jobs)

    if skipped_jobs:
        await _mark_jobs_skipped(db, skipped_jobs)

    if not jobs_in_db:
        await db.commit()
        return 0, 0, skipped, []

    success, errors, failed = await _embed_and_save(db, jobs_in_db, texts, embedder, batch_num, retry_attempt)
    return success, errors, skipped, failed


def _prepare_job_texts(jobs: list[Job]) -> tuple[list[Job], list[str], list[tuple[UUID, str]]]:
    """Prepare job texts for embedding, filtering invalid ones."""
    jobs_in_db = []
    texts = []
    skipped_jobs: list[tuple[UUID, str]] = []
    skipped_entries: list[dict[str, Any]] = []
    log_path = _get_skipped_jobs_log_path()
    timestamp = datetime.now(timezone.utc).isoformat()

    for job in jobs:
        desc_raw = getattr(job, "description_text", None)
        desc_str = str(desc_raw) if desc_raw is not None else ""
        text = clean_text_for_embedding(desc_str)
        text_length = len(text)

        if not text:
            skipped_jobs.append((job.id, "empty_text"))
            skipped_entries.append(
                {
                    "timestamp": timestamp,
                    "job_id": str(job.id),
                    "company": job.company,
                    "title": job.title,
                    "apply_url": job.apply_url,
                    "reason": "empty_text",
                    "text_length": text_length,
                }
            )
            if len(skipped_entries) >= LOG_FLUSH_BATCH_SIZE:
                _append_jsonl_batch(log_path, skipped_entries)
                skipped_entries.clear()
            continue
        if text_length < MIN_EMBEDDABLE_TEXT_LENGTH:
            skipped_jobs.append((job.id, "too_short"))
            skipped_entries.append(
                {
                    "timestamp": timestamp,
                    "job_id": str(job.id),
                    "company": job.company,
                    "title": job.title,
                    "apply_url": job.apply_url,
                    "reason": "too_short",
                    "text_length": text_length,
                }
            )
            if len(skipped_entries) >= LOG_FLUSH_BATCH_SIZE:
                _append_jsonl_batch(log_path, skipped_entries)
                skipped_entries.clear()
            continue

        jobs_in_db.append(job)
        texts.append(text)

    if skipped_entries:
        _append_jsonl_batch(log_path, skipped_entries)

    return jobs_in_db, texts, skipped_jobs


async def _mark_jobs_skipped(db: AsyncSession, skipped_jobs: list[tuple[UUID, str]]) -> None:
    """Persist permanent embedding skip markers so unembeddable jobs do not loop forever."""
    if not skipped_jobs:
        return

    skipped_at = datetime.now(timezone.utc)
    for job_id, reason in skipped_jobs:
        await db.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(
                embedding_skip_reason=reason,
                embedding_skipped_at=skipped_at,
            )
        )


async def _embed_and_save(
    db: AsyncSession,
    jobs: list[Job],
    texts: list[str],
    embedder: EmbeddingService,
    batch_num: int,
    retry_attempt: int,
) -> tuple[int, int, list[tuple[Job, BaseException]]]:
    """Embed texts and save to database."""
    success = 0
    errors = 0
    failed: list[tuple[Job, BaseException]] = []
    api_batch_size = get_config().embeddings.api_batch_size
    embeddings = None  # ensure defined even if all sub-batches error

    for i in range(0, len(texts), api_batch_size):
        batch_texts = texts[i : i + api_batch_size]
        batch_jobs = jobs[i : i + api_batch_size]

        try:
            embeddings = await embedder.embed_many(batch_texts, batch_size=api_batch_size)
            for job, embedding in zip(batch_jobs, embeddings):
                job.description_embedding = embedding
                job.embedding_skip_reason = None
                job.embedding_skipped_at = None
                db.add(job)
                success += 1
        except asyncio.CancelledError:
            logger.warning(f"  Batch {batch_num} cancelled during embedding")
            raise
        except Exception as e:
            batch_success, batch_errors, batch_failed = _handle_batch_error(batch_jobs, e, batch_num, retry_attempt)
            success += batch_success
            errors += batch_errors
            failed.extend(batch_failed)

    await db.commit()
    db.expunge_all()  # detach Job ORM objects so they can be GC'd immediately

    # Memory management: clear embedding references
    del embeddings

    return success, errors, failed


def _handle_batch_error(
    batch_jobs: list[Job],
    error: BaseException,
    batch_num: int,
    retry_attempt: int,
) -> tuple[int, int, list[tuple[Job, BaseException]]]:
    """Handle an error during batch embedding."""
    error_type, is_retryable = _classify_error(error)
    failed: list[tuple[Job, BaseException]] = []

    if is_retryable:
        for job in batch_jobs:
            failed.append((job, error))
        logger.warning(f"  Batch {batch_num} sub-batch error (retryable): {error_type} - {error}")
        return 0, 0, failed

    for job in batch_jobs:
        _log_failed_job(job, error_type, str(error), will_retry=False, retry_attempt=retry_attempt)
    logger.warning(f"  Batch {batch_num} sub-batch error (permanent): {error_type} - {error}")
    return 0, len(batch_jobs), failed


async def _process_with_semaphore(
    semaphore: asyncio.Semaphore,
    job_ids: list[UUID],
    embedder: EmbeddingService,
    batch_num: int,
    retry_attempt: int = 0,
) -> tuple[int, int, int, list[tuple[Job, BaseException]]]:
    """Process a batch with semaphore-controlled concurrency."""
    import gc
    from pipeline.embeddings.enrichment import reset_embedder

    async with semaphore:
        async with AsyncSessionLocal() as db:
            jobs = await _fetch_jobs_by_ids(db, job_ids)
            result = await _process_batch(db, jobs, embedder, batch_num, retry_attempt=retry_attempt)
            success, errors, skipped, failed = result
            logger.info(
                f"  Batch {batch_num}: {success} success, {errors} errors, {skipped} skipped"
                + (f" (retry {retry_attempt})" if retry_attempt > 0 else "")
            )

            # Memory management: every 50 batches, reset embedder and gc
            if batch_num % 50 == 0:
                reset_embedder()
                gc.collect()

            return result
