"""Embeddings generation module - create vector embeddings for job matching."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from app.models import Job
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

PARALLEL_BATCHES = 3
EMBEDDING_BATCH_SIZE = 10


def _get_skipped_jobs_log_path() -> Path:
    """Get today's log file path for skipped jobs."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return LOGS_DIR / f"skipped_jobs_{today}.jsonl"


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


def clean_text(text: str) -> str:
    """Clean and truncate text for embedding."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    ascii_chars = sum(1 for c in text if ord(c) < 128)
    is_mostly_ascii = len(text) == 0 or (ascii_chars / len(text)) > 0.8

    max_chars = 6000 if is_mostly_ascii else 2000

    return text[:max_chars]


async def _fetch_jobs_batch(batch_size: int) -> list[Job]:
    """Fetch a batch of jobs without embeddings."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Job).where(Job.description_embedding.is_(None)).limit(batch_size)
        )
        jobs = result.scalars().all()
        return list(jobs)


async def _process_batch(
    jobs: list[Job],
    embedder: EmbeddingService,
    batch_num: int,
) -> tuple[int, int, int]:
    """Process a single batch of jobs with embeddings.

    Returns:
        Tuple of (success_count, error_count, skipped_count)
    """
    if not jobs:
        return 0, 0, 0

    async with AsyncSessionLocal() as db:
        jobs_in_db = []
        texts = []

        for job in jobs:
            text = clean_text(job.description_text)
            text_length = len(text) if text else 0

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
            return 0, 0, skipped

        success = 0
        errors = 0

        for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch_texts = texts[i : i + EMBEDDING_BATCH_SIZE]
            batch_jobs = jobs_in_db[i : i + EMBEDDING_BATCH_SIZE]

            try:
                embeddings = await embedder.embed_many(batch_texts, batch_size=EMBEDDING_BATCH_SIZE)
                for job, embedding in zip(batch_jobs, embeddings):
                    job.description_embedding = embedding
                    db.add(job)
                    success += 1
            except Exception as e:
                errors += len(batch_jobs)
                if errors <= 3:
                    logger.warning(f"  Batch {batch_num} embedding error: {e}")

        await db.commit()
        return success, errors, skipped


async def generate_embeddings(
    session: AsyncSession | None = None, batch_size: int = 50
) -> tuple[int, int]:
    """Generate embeddings for jobs without them using parallel processing.

    Args:
        session: Optional existing session (unused, kept for API compatibility)
        batch_size: Number of jobs to process per parallel batch

    Returns:
        Tuple of (success_count, error_count)
    """
    logger.info("=" * 60)
    logger.info("STEP 4: Generating embeddings (parallel mode)...")
    logger.info("=" * 60)

    total_success, total_errors, total_skipped = 0, 0, 0

    try:
        embedder = EmbeddingService()
        logger.info(f"Using embedding provider: {embedder._provider}, model: {embedder._model}")
    except Exception as e:
        logger.error(f"Failed to initialize embedding service: {e}")
        return 0, 0

    async with AsyncSessionLocal() as count_db:
        count_result = await count_db.execute(
            select(func.count()).select_from(Job).where(Job.description_embedding.is_(None))
        )
        total_jobs = count_result.scalar() or 0
        logger.info(f"Found {total_jobs} jobs without embeddings")

    if total_jobs == 0:
        logger.info("No jobs need embeddings")
        return 0, 0

    semaphore = asyncio.Semaphore(PARALLEL_BATCHES)
    batch_num = 0

    async def process_with_semaphore(jobs: list[Job], num: int) -> tuple[int, int, int]:
        async with semaphore:
            result = await _process_batch(jobs, embedder, num)
            logger.info(
                f"  Batch {num}: {result[0]} success, {result[1]} errors, {result[2]} skipped"
            )
            return result

    while True:
        pending_batches = []

        for _ in range(PARALLEL_BATCHES):
            batch_num += 1
            jobs = await _fetch_jobs_batch(batch_size)

            if not jobs:
                break

            pending_batches.append(process_with_semaphore(jobs, batch_num))

        if not pending_batches:
            break

        results = await asyncio.gather(*pending_batches, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Batch failed with exception: {result}")
                total_errors += batch_size
            else:
                success, errors, skipped = result
                total_success += success
                total_errors += errors
                total_skipped += skipped

        remaining = total_jobs - total_success - total_errors - total_skipped
        logger.info(
            f"Progress: {total_success} embedded, {total_errors} errors, "
            f"{total_skipped} skipped, ~{remaining} remaining"
        )

    logger.info(
        f"Embedding complete: {total_success} success, {total_errors} errors, "
        f"{total_skipped} skipped"
    )
    return total_success, total_errors
