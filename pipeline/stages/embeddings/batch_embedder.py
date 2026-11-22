"""Batch processing logic for embedding generation."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import String, cast, column, func, or_, select, update, values
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from internnexus_core.text import clean_text_for_embedding, embedding_input_hash
from pipeline.infra.daily_json_logger import DailyJsonLogger
from pipeline.infra.db import AsyncSessionLocal
from pipeline.infra.embedding import QueryEmbeddingService as EmbeddingService
from pipeline.infra.models import Job
from pipeline.repositories.job_text_sql import embedding_candidate_text_sql
from pipeline.stages.embeddings.batch_records import BatchResult, classify_error
from pipeline.infra.pipeline_config import get_config

logger = logging.getLogger(__name__)

LOG_FLUSH_BATCH_SIZE = 100
MIN_EMBEDDABLE_TEXT_LENGTH = 30


def _embedding_recency_filter():
    """Restrict embedding candidates to jobs matching can actually return.

    The match query filters candidates to ``matchable_within_days`` after
    vector retrieval (jobs without ``posted_at`` are retained), so embedding
    older rows only adds storage and index churn.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(
        days=get_config().embeddings.matchable_within_days
    )
    return or_(Job.posted_at.is_(None), Job.posted_at >= cutoff)



def _skipped_log_error(error: Exception) -> None:
    logger.debug("Failed to log skipped job: %s", error)


def _failed_log_error(error: Exception) -> None:
    logger.debug("Failed to log failed job: %s", error)


_skipped_logger = DailyJsonLogger(
    directory=lambda: get_config().logging.logs_dir,
    prefix="skipped_jobs",
    on_error=_skipped_log_error,
)
_failed_logger = DailyJsonLogger(
    directory=lambda: get_config().logging.logs_dir,
    prefix="failed_jobs",
    on_error=_failed_log_error,
)


def _get_skipped_jobs_log_path() -> Path:
    """Get today's log file path for skipped jobs."""
    return _skipped_logger.path_for()


def _get_failed_jobs_log_path() -> Path:
    """Get today's log file path for failed jobs."""
    return _failed_logger.path_for()


def _append_jsonl_batch(path: Path, entries: list[dict[str, Any]]) -> None:
    """Append multiple JSONL records in a single write."""
    target = _failed_logger if path.name.startswith("failed_jobs_") else _skipped_logger
    target.log_many(entries)


def _log_failed_job(
    job_id: UUID,
    error_type: str,
    error_message: str,
    will_retry: bool,
    retry_attempt: int = 0,
    *,
    company: str = "",
    title: str = "",
) -> None:
    """Log a failed job to the daily log file."""
    entry: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "job_id": str(job_id),
        "company": company,
        "title": title,
        "error_type": error_type,
        "error_message": error_message[:500] if error_message else "",
        "will_retry": will_retry,
    }
    if retry_attempt > 0:
        entry["retry_attempt"] = retry_attempt
    _failed_logger.log(entry)


def _classify_error(error: BaseException) -> tuple[str, bool]:
    """Classify error as (error_type, is_retryable)."""
    return classify_error(error)


async def _fetch_job_ids_batch(
    db: AsyncSession,
    batch_size: int,
    after_id: UUID | None = None,
    excluded_ids: set[UUID] | None = None,
) -> list[UUID]:
    """Fetch a batch of job IDs without embeddings or permanent skip markers."""
    cleaned_text = embedding_candidate_text_sql()
    stmt = (
        select(Job.id)
        .where(Job.is_active.is_(True))
        .where(Job.description_embedding.is_(None))
        .where(Job.embedding_skip_reason.is_(None))
        .where(_embedding_recency_filter())
        .where(func.length(cleaned_text) >= MIN_EMBEDDABLE_TEXT_LENGTH)
        .order_by(Job.id)
        .limit(batch_size)
    )
    if excluded_ids:
        stmt = stmt.where(Job.id.notin_(excluded_ids))
    if after_id is not None:
        stmt = stmt.where(Job.id > after_id)

    result = await db.execute(stmt)
    job_ids = result.scalars().all()
    return list(job_ids)


async def _fetch_jobs_by_ids(db: AsyncSession, job_ids: list[UUID]) -> list[Job]:
    """Fetch specific jobs by ID for retry."""
    if not job_ids:
        return []
    result = await db.execute(
        select(Job)
        .where(Job.id.in_(job_ids))
        .options(
            defer(Job.description_embedding),
            defer(Job.search_vector),
        )
    )
    jobs = result.scalars().all()
    return list(jobs)


async def _get_remaining_count(db: AsyncSession) -> int:
    """Get the current count of jobs without embeddings."""
    cleaned_text = embedding_candidate_text_sql()
    result = await db.execute(
        select(func.count())
        .select_from(Job)
        .where(Job.is_active.is_(True))
        .where(Job.description_embedding.is_(None))
        .where(Job.embedding_skip_reason.is_(None))
        .where(_embedding_recency_filter())
        .where(func.length(cleaned_text) >= MIN_EMBEDDABLE_TEXT_LENGTH)
    )
    return result.scalar() or 0


async def _process_batch(
    db: AsyncSession,
    jobs: list[Job],
    embedder: EmbeddingService,
    batch_num: int,
    retry_attempt: int = 0,
) -> BatchResult:
    """Process a single batch of jobs with embeddings."""
    if not jobs:
        return BatchResult(0, 0, 0, [])

    jobs_in_db, texts, skipped_jobs = _prepare_job_texts(jobs)
    skipped = len(skipped_jobs)

    if skipped_jobs:
        await _mark_jobs_skipped(db, skipped_jobs)

    if not jobs_in_db:
        await db.commit()
        return BatchResult(0, 0, skipped, [])

    success, errors, failed = await _embed_and_save(db, jobs_in_db, texts, embedder, batch_num, retry_attempt)
    return BatchResult(success, errors, skipped, failed)


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
    batch = values(
        column("id", PG_UUID(as_uuid=True)),
        column("reason", String),
        name="v",
    ).data(list(skipped_jobs))

    await db.execute(
        update(Job)
        .where(Job.id == batch.c.id)
        .values(
            embedding_skip_reason=cast(batch.c.reason, String),
            embedding_skipped_at=skipped_at,
        )
        .execution_options(synchronize_session=False)
    )


def _embedding_update_stmt(rows: list[tuple[UUID, list[float], str]]):
    """Build one multi-row UPDATE for a batch of freshly computed embeddings.

    Replaces one `UPDATE ... WHERE jobs.id = $1` round trip per job (197,649 of
    them in the last measured window) with a single `UPDATE ... FROM (VALUES ...)`.
    Postgres still writes one row version per row, so this does not by itself
    reduce WAL or physical writes -- it removes the per-row round trip, parse,
    plan, and ORM overhead. The write-volume reductions come from dropping the
    HNSW index and shrinking the embedding column.

    Every guard from the per-row form is preserved, so a row is still only
    written when it is active, unembedded, unskipped, and its input hash either
    matches or is unset. `rowcount` therefore keeps its original meaning: the
    number of jobs actually embedded.

    The embedding column type is read from the model rather than hardcoded so
    this keeps working when the column changes dimension or precision. The
    explicit CAST matters: inside a multi-row VALUES the parameters resolve to
    `unknown`/`text`, which has no implicit coercion to `vector`.
    """
    embedding_type = Job.__table__.c.description_embedding.type
    batch = values(
        column("id", PG_UUID(as_uuid=True)),
        column("emb", embedding_type),
        column("hash", String),
        name="v",
    ).data(rows)

    return (
        update(Job)
        .where(Job.id == batch.c.id)
        .where(Job.is_active.is_(True))
        .where(Job.description_embedding.is_(None))
        .where(Job.embedding_skip_reason.is_(None))
        .where(
            or_(
                Job.embedding_input_hash == batch.c.hash,
                Job.embedding_input_hash.is_(None),
            )
        )
        .values(
            description_embedding=cast(batch.c.emb, embedding_type),
            embedding_input_hash=cast(batch.c.hash, String),
            embedding_skip_reason=None,
            embedding_skipped_at=None,
        )
        .execution_options(synchronize_session=False)
    )


async def _embed_and_save(
    db: AsyncSession,
    jobs: list[Job],
    texts: list[str],
    embedder: EmbeddingService,
    batch_num: int,
    retry_attempt: int,
) -> tuple[int, int, list[tuple[UUID, BaseException]]]:
    """Embed texts and save to database."""
    success = 0
    errors = 0
    failed: list[tuple[UUID, BaseException]] = []
    api_batch_size = get_config().embeddings.api_batch_size
    embeddings = None  # ensure defined even if all sub-batches error

    for i in range(0, len(texts), api_batch_size):
        batch_texts = texts[i : i + api_batch_size]
        batch_jobs = jobs[i : i + api_batch_size]

        try:
            embeddings = await embedder.embed_many(batch_texts, batch_size=api_batch_size)
            rows = [
                (job.id, embedding, embedding_input_hash(job.description_text))
                for job, embedding in zip(batch_jobs, embeddings)
            ]
            if rows:
                result = await db.execute(_embedding_update_stmt(rows))
                success += int(getattr(result, "rowcount", 0) or 0)
        except asyncio.CancelledError:
            logger.warning(f"  Batch {batch_num} cancelled during embedding")
            raise
        except Exception as e:  # noqa: BLE001  # any embedding failure is classified and recorded per job
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
) -> tuple[int, int, list[tuple[UUID, BaseException]]]:
    """Handle an error during batch embedding."""
    error_type, is_retryable = _classify_error(error)
    failed: list[tuple[UUID, BaseException]] = []

    if is_retryable:
        for job in batch_jobs:
            failed.append((job.id, error))
        logger.warning(f"  Batch {batch_num} sub-batch error (retryable): {error_type} - {error}")
        return 0, 0, failed

    for job in batch_jobs:
        _log_failed_job(
            job.id,
            error_type,
            str(error),
            will_retry=False,
            retry_attempt=retry_attempt,
            company=job.company,
            title=job.title,
        )
    logger.warning(f"  Batch {batch_num} sub-batch error (permanent): {error_type} - {error}")
    return 0, len(batch_jobs), failed


async def _process_with_semaphore(
    semaphore: asyncio.Semaphore,
    job_ids: list[UUID],
    embedder: EmbeddingService,
    batch_num: int,
    retry_attempt: int = 0,
) -> BatchResult:
    """Process a batch with semaphore-controlled concurrency."""
    import gc

    async with semaphore:
        async with AsyncSessionLocal() as db:
            jobs = await _fetch_jobs_by_ids(db, job_ids)
            result = await _process_batch(db, jobs, embedder, batch_num, retry_attempt=retry_attempt)
            success, errors, skipped, _ = result
            logger.info(
                f"  Batch {batch_num}: {success} success, {errors} errors, {skipped} skipped"
                + (f" (retry {retry_attempt})" if retry_attempt > 0 else "")
            )

            # Bound retained ORM/native memory during large runs.
            if batch_num % 50 == 0:
                gc.collect()

            return result
