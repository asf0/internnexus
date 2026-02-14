"""Embeddings generation module - create vector embeddings for job matching."""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from app.models import Job
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

# Log directory for skipped jobs
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


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
                # Extract date from filename: skipped_jobs_YYYY-MM-DD.jsonl
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
    """Clean and truncate text for embedding.

    Uses higher limit for ASCII text (English) and lower limit for
    non-ASCII text (Japanese, Chinese, etc.) which uses more tokens per char.
    """
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Check if text is mostly ASCII (a-z, 0-9, common punctuation)
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    is_mostly_ascii = len(text) == 0 or (ascii_chars / len(text)) > 0.8

    # Use appropriate limit based on character type
    max_chars = 6000 if is_mostly_ascii else 2000

    return text[:max_chars]


async def generate_embeddings(
    session: AsyncSession | None = None, batch_size: int = 50
) -> tuple[int, int]:
    """Generate embeddings for jobs without them.

    Processes jobs in batches, with each batch using a separate session to avoid
    SQLAlchemy greenlet issues after commit.

    Args:
        session: Optional existing session. If None, creates new sessions per batch.
        batch_size: Number of embeddings to generate per batch

    Returns:
        Tuple of (success_count, error_count)
    """
    logger.info("=" * 60)
    logger.info("STEP 4: Generating embeddings...")
    logger.info("=" * 60)

    total_success, total_errors, total_skipped = 0, 0, 0
    batch_num = 0

    try:
        embedder = EmbeddingService()
        logger.info(f"Using embedding provider: {embedder._provider}, model: {embedder._model}")
    except Exception as e:
        logger.error(f"Failed to initialize embedding service: {e}")
        return 0, 0

    # Get total count of jobs needing embeddings
    async with AsyncSessionLocal() as count_db:
        count_result = await count_db.execute(
            select(func.count()).select_from(Job).where(Job.description_embedding.is_(None))
        )
        total_jobs = count_result.scalar()
        logger.info(f"Found {total_jobs} jobs without embeddings")

    # Calculate expected batches (with safety margin)
    expected_batches = (total_jobs // batch_size) + 1
    max_batches = expected_batches * 2  # 2x safety margin for retries
    logger.info(f"Expected ~{expected_batches} batches (max: {max_batches})")

    while True:
        batch_num += 1

        # Safety check to prevent infinite loops
        if batch_num > max_batches:
            logger.warning(f"Reached max_batches limit ({max_batches}). Stopping.")
            logger.warning(
                f"There may be {total_jobs - total_success - total_errors - total_skipped} "
                "jobs that couldn't be processed."
            )
            break

        # Create a new session for each batch
        async with AsyncSessionLocal() as db:
            # Query only batch_size jobs without embeddings
            result = await db.execute(
                select(Job).where(Job.description_embedding.is_(None)).limit(batch_size)
            )
            jobs = result.scalars().all()

            if not jobs:
                # No more jobs to process
                break

            logger.info(f"Processing batch {batch_num}: {len(jobs)} jobs")

            batch_success, batch_errors, batch_skipped = 0, 0, 0
            batch_empty_text, batch_too_short = 0, 0

            for i, job in enumerate(jobs):
                try:
                    text = clean_text(job.description_text)
                    text_length = len(text) if text else 0
                    if not text:
                        batch_empty_text += 1
                        batch_skipped += 1
                        _log_skipped_job(job, "empty_text", text_length)
                        continue
                    if text_length < 30:
                        batch_too_short += 1
                        batch_skipped += 1
                        _log_skipped_job(job, "too_short", text_length)
                        continue

                    embedding = await embedder.embed(text)
                    job.description_embedding = embedding
                    batch_success += 1

                    if (i + 1) % 25 == 0:
                        logger.info(f"  [{i + 1}/{len(jobs)}] {job.company} - {job.title[:40]}...")

                except Exception as e:
                    batch_errors += 1
                    if batch_errors <= 3:
                        logger.warning(f"  [{i + 1}/{len(jobs)}] Error: {e}")

            # Commit this batch
            await db.commit()

            total_success += batch_success
            total_errors += batch_errors
            total_skipped += batch_skipped

            # Progress logging
            if batch_num % 100 == 0 or batch_num == 1:
                progress = min((batch_num / expected_batches) * 100, 100)
                logger.info(
                    f"Progress: {batch_num}/{expected_batches} batches ({progress:.1f}%) - "
                    f"{total_success} success, {total_errors} errors, {total_skipped} skipped"
                )

            # Build skip reasons summary
            skip_reasons = []
            if batch_empty_text > 0:
                skip_reasons.append(f"{batch_empty_text} empty text")
            if batch_too_short > 0:
                skip_reasons.append(f"{batch_too_short} too short")
            skip_details = f" ({', '.join(skip_reasons)})" if skip_reasons else ""

            logger.info(
                f"Batch {batch_num} complete: {batch_success} success, {batch_errors} errors, "
                f"{batch_skipped} skipped{skip_details} "
                f"(total: {total_success} success, {total_errors} errors, {total_skipped} skipped)"
            )

    logger.info(
        f"Embedding complete: {total_success} success, {total_errors} errors, "
        f"{total_skipped} skipped"
    )
    return total_success, total_errors
