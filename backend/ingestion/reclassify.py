"""Reclassify visa sponsorship for existing jobs."""

from __future__ import annotations

import asyncio
import csv
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from app.models import Job
from app.services.visa_classifier import VisaClassifier

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """Clean HTML and truncate text."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+", " ", text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Use 3000 char limit as requested
    ascii_chars = sum(1 for c in text if ord(c) < 128)
    is_mostly_ascii = len(text) == 0 or (ascii_chars / len(text)) > 0.8
    max_chars = 3000 if is_mostly_ascii else 2000

    return text[:max_chars]


def _truncate_text(text: str, max_length: int = 30) -> str:
    """Truncate text to max_length, adding ... if truncated."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


async def classify_single_job(job: Job, classifier: VisaClassifier) -> tuple:
    """Classify a single job using thread pool for concurrency.

    Returns: (job, error_message, classification_result, token_usage)
    """
    try:
        text = clean_text(job.description_text)
        if not text:
            return job, "empty", None, None

        # Run sync classify in thread pool
        result, tokens = await asyncio.to_thread(classifier.classify, text)
        return job, None, result, tokens
    except Exception as e:
        return job, str(e), None, None


def _write_csv_row(
    csv_writer,
    csv_file_handle,
    job_id,
    company,
    title,
    visa,
    f1,
    total_tokens,
    prompt_tokens,
    completion_tokens,
    timestamp,
    error=None,
):
    """Write a single row to the CSV file and flush immediately."""
    csv_writer.writerow(
        {
            "job_id": str(job_id),
            "company": company or "",
            "title": title or "",
            "visa": visa if visa is not None else "",
            "f1": f1 if f1 is not None else "",
            "total_tokens": total_tokens or 0,
            "prompt_tokens": prompt_tokens or 0,
            "completion_tokens": completion_tokens or 0,
            "timestamp": timestamp,
            "error": error or "",
        }
    )
    # Flush to disk immediately
    csv_file_handle.flush()


def _write_json_line(
    json_file_handle,
    job_id,
    company,
    title,
    visa,
    f1,
    total_tokens,
    prompt_tokens,
    completion_tokens,
    timestamp,
    error_msg=None,
):
    """Write a single JSON line and flush immediately."""
    record = {
        "job_id": str(job_id),
        "company": company or "",
        "title": title or "",
        "visa": visa if visa is not None else None,
        "f1": f1 if f1 is not None else None,
        "total_tokens": total_tokens or 0,
        "prompt_tokens": prompt_tokens or 0,
        "completion_tokens": completion_tokens or 0,
        "timestamp": timestamp,
        "error": error_msg or None,
    }
    json_file_handle.write(json.dumps(record) + "\n")
    # Flush to disk immediately
    json_file_handle.flush()


async def reclassify_visa(only_null: bool = True, batch_size: int = 50, parallel: int = 4) -> dict:
    """Re-run visa classification on existing jobs."""

    # Setup file logging
    logs_dir = Path(__file__).resolve().parents[1] / "logs"
    logs_dir.mkdir(exist_ok=True)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = logs_dir / f"visa_classifications_{timestamp_str}.csv"
    json_file = logs_dir / f"visa_classifications_{timestamp_str}.jsonl"

    # Open files for writing
    csv_file_handle = open(csv_file, "w", newline="", encoding="utf-8")
    csv_writer = csv.DictWriter(
        csv_file_handle,
        fieldnames=[
            "job_id",
            "company",
            "title",
            "visa",
            "f1",
            "total_tokens",
            "prompt_tokens",
            "completion_tokens",
            "timestamp",
            "error",
        ],
    )
    csv_writer.writeheader()
    csv_file_handle.flush()

    json_file_handle = open(json_file, "w", encoding="utf-8")
    json_file_handle.flush()

    logger.info(f"Logging classifications to: {csv_file}")
    logger.info(f"Logging classifications to: {json_file}")

    classifier = VisaClassifier()

    # Count jobs to process
    async with AsyncSessionLocal() as count_db:
        query = select(func.count()).select_from(Job)
        if only_null:
            query = query.where(Job.visa_sponsored.is_(None))
        count_result = await count_db.execute(query)
        total_jobs = count_result.scalar()
        logger.info(f"Found {total_jobs} jobs to process")

    if total_jobs == 0:
        logger.info("No jobs to reclassify")
        csv_file_handle.close()
        json_file_handle.close()
        return {"processed": 0, "success": 0, "errors": 0}

    # Statistics tracking
    total_processed = 0
    total_success = 0
    total_errors = 0
    total_tokens_used = 0
    start_time = datetime.now()

    logger.info(f"Processing {total_jobs} jobs (parallel={parallel})")

    batch_num = 0
    while True:
        batch_num += 1

        async with AsyncSessionLocal() as db:
            # Query batch
            query = select(Job)
            if only_null:
                query = query.where(Job.visa_sponsored.is_(None))
            result = await db.execute(query.limit(batch_size))
            jobs = result.scalars().all()

            if not jobs:
                break

            batch_success = 0
            batch_errors = 0

            # Process in sub-batches of 'parallel' jobs
            for sub_start in range(0, len(jobs), parallel):
                sub_batch = jobs[sub_start : sub_start + parallel]

                # Create concurrent tasks for individual jobs
                tasks = [classify_single_job(job, classifier) for job in sub_batch]

                # Wait for all to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results
                for idx, res in enumerate(results):
                    job = sub_batch[idx]
                    job_index = sub_start + idx + 1
                    current_timestamp = datetime.now()
                    time_str = current_timestamp.strftime("%H:%M:%S")

                    if isinstance(res, Exception):
                        total_errors += 1
                        batch_errors += 1
                        # Extract company and title as strings
                        company_str = str(job.company) if job.company is not None else ""
                        title_str = str(job.title) if job.title is not None else ""
                        # Write error to both files
                        _write_csv_row(
                            csv_writer,
                            csv_file_handle,
                            job.id,
                            company_str,
                            title_str,
                            None,
                            None,
                            0,
                            0,
                            0,
                            current_timestamp.isoformat(),
                            str(res),
                        )
                        _write_json_line(
                            json_file_handle,
                            job.id,
                            company_str,
                            title_str,
                            None,
                            None,
                            0,
                            0,
                            0,
                            current_timestamp.isoformat(),
                            str(res),
                        )
                        continue

                    _, error, result, tokens = res

                    # Extract company and title as strings
                    company_str = str(job.company) if job.company is not None else ""
                    title_str = str(job.title) if job.title is not None else ""

                    if error == "empty":
                        # Write empty to both files
                        _write_csv_row(
                            csv_writer,
                            csv_file_handle,
                            job.id,
                            company_str,
                            title_str,
                            None,
                            None,
                            0,
                            0,
                            0,
                            current_timestamp.isoformat(),
                            "Empty description",
                        )
                        _write_json_line(
                            json_file_handle,
                            job.id,
                            company_str,
                            title_str,
                            None,
                            None,
                            0,
                            0,
                            0,
                            current_timestamp.isoformat(),
                            "Empty description",
                        )
                        continue
                    elif error:
                        total_errors += 1
                        batch_errors += 1
                        # Write error to both files
                        _write_csv_row(
                            csv_writer,
                            csv_file_handle,
                            job.id,
                            company_str,
                            title_str,
                            None,
                            None,
                            0,
                            0,
                            0,
                            current_timestamp.isoformat(),
                            error,
                        )
                        _write_json_line(
                            json_file_handle,
                            job.id,
                            company_str,
                            title_str,
                            None,
                            None,
                            0,
                            0,
                            0,
                            current_timestamp.isoformat(),
                            error,
                        )
                    else:
                        job.visa_sponsored = result.get("visa")
                        job.f1_friendly = result.get("f1")
                        total_success += 1
                        batch_success += 1

                        # Track tokens
                        job_tokens = tokens.get("total_tokens", 0) if tokens else 0
                        total_tokens_used += job_tokens

                        # Log every job with visa/f1 status
                        visa_status = "✓" if job.visa_sponsored else "✗"
                        f1_status = "✓" if job.f1_friendly else "✗"
                        logger.info(
                            f"[{job_index}/{batch_size}] | {_truncate_text(company_str, 32):32} | {_truncate_text(title_str, 40):40} | Visa: {visa_status} | F1: {f1_status} | Tokens: {job_tokens:,}"
                        )

                        # Write success to both files with tokens
                        _write_csv_row(
                            csv_writer,
                            csv_file_handle,
                            job.id,
                            company_str,
                            title_str,
                            result.get("visa"),
                            result.get("f1"),
                            tokens.get("total_tokens", 0) if tokens else 0,
                            tokens.get("prompt_tokens", 0) if tokens else 0,
                            tokens.get("completion_tokens", 0) if tokens else 0,
                            current_timestamp.isoformat(),
                        )
                        _write_json_line(
                            json_file_handle,
                            job.id,
                            company_str,
                            title_str,
                            result.get("visa"),
                            result.get("f1"),
                            tokens.get("total_tokens", 0) if tokens else 0,
                            tokens.get("prompt_tokens", 0) if tokens else 0,
                            tokens.get("completion_tokens", 0) if tokens else 0,
                            current_timestamp.isoformat(),
                        )

                    total_processed += 1

            await db.commit()

            # Log batch completion every batch
            remaining = total_jobs - total_processed
            logger.info(
                f"Batch {batch_num} complete ({total_processed}/{total_jobs} processed, {remaining} remaining)"
            )

    # Close files
    csv_file_handle.close()
    json_file_handle.close()

    elapsed = (datetime.now() - start_time).total_seconds()
    avg_tokens = total_tokens_used / total_success if total_success > 0 else 0

    logger.info("=" * 60)
    logger.info("RECLASSIFY COMPLETE")
    logger.info(f"  Total processed: {total_processed}")
    logger.info(f"  Success: {total_success}")
    logger.info(f"  Errors: {total_errors}")
    logger.info(f"  Total tokens: {total_tokens_used}")
    logger.info(f"  Avg tokens/job: {avg_tokens:.1f}")
    logger.info(f"  Elapsed: {elapsed:.1f}s")
    logger.info(f"  CSV file: {csv_file}")
    logger.info(f"  JSON file: {json_file}")
    logger.info("=" * 60)

    return {
        "processed": total_processed,
        "success": total_success,
        "errors": total_errors,
        "csv_file": str(csv_file),
        "json_file": str(json_file),
        "total_tokens": total_tokens_used,
        "avg_tokens": avg_tokens,
    }
