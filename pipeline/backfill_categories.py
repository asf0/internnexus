#!/usr/bin/env python3
"""Backfill job categories for existing jobs in the database.

This script processes jobs that have NULL job_category and classifies them
using the LLM-based classifier.

Usage:
    # Run full backfill
    uv run python -m pipeline.backfill_categories

    # Test with 100 jobs
    uv run python -m pipeline.backfill_categories --limit 100 --dry-run

    # Resume interrupted backfill
    uv run python -m pipeline.backfill_categories --resume

    # Custom batch size
    uv run python -m pipeline.backfill_categories --batch-size 50
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import signal
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

try:
    from pipeline.path_setup import ensure_project_paths
except ModuleNotFoundError:
    # Support direct script execution from inside pipeline/ directory.
    from path_setup import ensure_project_paths

ensure_project_paths()

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.classification import JobClassifier, get_classifier
from pipeline.repositories.sqlalchemy_repo import AsyncSessionLocal, Job

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Progress tracking file
PROGRESS_FILE = Path(__file__).parent / ".backfill_progress.json"

# Graceful shutdown flag
_shutdown_requested = False


def setup_signal_handlers() -> None:
    """Set up signal handlers for graceful shutdown."""
    global _shutdown_requested

    def handle_signal(signum, frame):
        global _shutdown_requested
        _shutdown_requested = True
        logger.warning("\nShutdown requested. Finishing current batch and saving progress...")

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)


class ProgressTracker:
    """Track backfill progress for resumption."""

    def __init__(self, progress_file: Path = PROGRESS_FILE):
        self.progress_file = progress_file
        self.data = self._load_progress()

    def _load_progress(self) -> dict[str, Any]:
        """Load progress from file if it exists."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not load progress file: {e}")
        return self._default_progress()

    def _default_progress(self) -> dict[str, Any]:
        """Return default progress structure."""
        return {
            "started_at": None,
            "last_updated": None,
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "last_job_id": None,
            "processed_job_ids": [],
            "new_categories": {},
            "status": "not_started",
        }

    def save(self, **kwargs: Any) -> None:
        """Save progress to file."""
        self.data.update(kwargs)
        self.data["last_updated"] = datetime.now(timezone.utc).isoformat()
        try:
            with open(self.progress_file, "w") as f:
                json.dump(self.data, f, indent=2, default=str)
        except IOError as e:
            logger.error(f"Could not save progress file: {e}")

    def mark_started(self) -> None:
        """Mark the backfill as started."""
        self.save(
            started_at=datetime.now(timezone.utc).isoformat(),
            status="in_progress",
        )

    def mark_completed(self) -> None:
        """Mark the backfill as completed."""
        self.save(status="completed")

    def update_progress(
        self,
        processed: int,
        successful: int,
        failed: int,
        last_job_id: str | None,
        new_categories: dict[str, int] | None = None,
    ) -> None:
        """Update progress after processing a batch."""
        updates = {
            "total_processed": self.data["total_processed"] + processed,
            "successful": self.data["successful"] + successful,
            "failed": self.data["failed"] + failed,
            "last_job_id": str(last_job_id) if last_job_id else None,
        }
        if new_categories:
            current_categories = self.data.get("new_categories", {})
            for cat, count in new_categories.items():
                current_categories[cat] = current_categories.get(cat, 0) + count
            updates["new_categories"] = current_categories
        self.save(**updates)

    def get_processed_ids(self) -> set[str]:
        """Get set of already processed job IDs."""
        return set(self.data.get("processed_job_ids", []))

    def add_processed_ids(self, job_ids: list[str]) -> None:
        """Add processed job IDs to tracking."""
        current = set(self.data.get("processed_job_ids", []))
        current.update(job_ids)
        # Keep only last 10000 IDs to avoid file bloat
        # We rely on last_job_id for resume position
        self.data["processed_job_ids"] = list(current)[-10000:]

    def get_resume_position(self) -> str | None:
        """Get the last processed job ID for resumption."""
        return self.data.get("last_job_id")

    def reset(self) -> None:
        """Reset progress for a fresh start."""
        self.data = self._default_progress()
        if self.progress_file.exists():
            self.progress_file.unlink()
        logger.info("Progress reset")

    @property
    def total_processed(self) -> int:
        return self.data.get("total_processed", 0)

    @property
    def successful(self) -> int:
        return self.data.get("successful", 0)

    @property
    def failed(self) -> int:
        return self.data.get("failed", 0)


class CategoryBackfiller:
    """Backfill job categories using LLM classification."""

    def __init__(
        self,
        batch_size: int = 100,
        limit: int | None = None,
        dry_run: bool = False,
        resume: bool = False,
    ):
        self.batch_size = batch_size
        self.limit = limit
        self.dry_run = dry_run
        self.resume = resume
        self.progress = ProgressTracker()
        self.classifier: JobClassifier | None = None
        self.category_counter: Counter = Counter()
        self.start_time: float = 0

    async def initialize(self) -> bool:
        """Initialize the classifier and verify connectivity."""
        try:
            self.classifier = await get_classifier()
            logger.info(f"Classifier initialized: {self.classifier._model}")
            logger.info(f"Classification URL: {self.classifier._base_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize classifier: {e}")
            logger.error(
                "Make sure Ollama is running and the model is available. Run: ollama pull qwen3:4b"
            )
            return False

    async def get_total_uncategorized(self, session: AsyncSession) -> int:
        """Get total count of jobs without categories."""
        result = await session.execute(select(func.count(Job.id)).where(Job.job_category.is_(None)))
        return result.scalar() or 0

    async def fetch_batch(self, session: AsyncSession, after_id: UUID | None = None) -> list[Job]:
        """Fetch a batch of jobs without categories."""
        query = (
            select(Job).where(Job.job_category.is_(None)).order_by(Job.id).limit(self.batch_size)
        )

        if after_id:
            query = query.where(Job.id > after_id)

        result = await session.execute(query)
        return list(result.scalars().all())

    async def classify_batch(self, jobs: list[Job]) -> list[tuple[Job, str | None]]:
        """Classify a batch of jobs."""
        if not self.classifier:
            return [(job, None) for job in jobs]

        # Prepare classification inputs
        job_data = [(job.title, job.description_text or "") for job in jobs]

        # Classify all jobs in the batch
        categories = await self.classifier.classify_batch(job_data)

        return list(zip(jobs, categories))

    async def update_categories(
        self, session: AsyncSession, results: list[tuple[Job, str | None]]
    ) -> tuple[int, int, dict[str, int]]:
        """Update job categories in the database."""
        successful = 0
        failed = 0
        new_categories: dict[str, int] = {}

        for job, category in results:
            if category:
                successful += 1
                new_categories[category] = new_categories.get(category, 0) + 1
                self.category_counter[category] += 1

                if not self.dry_run:
                    try:
                        await session.execute(
                            update(Job).where(Job.id == job.id).values(job_category=category)
                        )
                    except Exception as e:
                        logger.error(f"Failed to update job {job.id}: {e}")
                        successful -= 1
                        failed += 1
            else:
                failed += 1

        if not self.dry_run:
            await session.commit()

        return successful, failed, new_categories

    def print_progress(
        self,
        batch_num: int,
        batch_success: int,
        batch_failed: int,
        total_remaining: int,
        batch_time: float,
    ) -> None:
        """Print progress information with ETA."""
        total_processed = self.progress.total_processed + batch_success + batch_failed
        total_successful = self.progress.successful + batch_success
        total_failed = self.progress.failed + batch_failed

        elapsed = time.time() - self.start_time
        rate = total_processed / elapsed if elapsed > 0 else 0

        # Estimate remaining time
        if rate > 0 and total_remaining > 0:
            eta_seconds = total_remaining / rate
            eta_str = self._format_duration(eta_seconds)
        else:
            eta_str = "calculating..."

        # Progress bar
        progress_pct = (
            (total_processed / (total_processed + total_remaining)) * 100
            if total_remaining > 0
            else 100
        )
        bar_width = 30
        filled = int(bar_width * progress_pct / 100)
        bar = "█" * filled + "░" * (bar_width - filled)

        print(
            f"\r[{bar}] {progress_pct:.1f}% | "
            f"Batch {batch_num} | "
            f"✓ {total_successful} | ✗ {total_failed} | "
            f"ETA: {eta_str} | "
            f"{rate:.1f} jobs/s",
            end="",
            flush=True,
        )

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable form."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"

    def print_final_stats(self, elapsed: float) -> None:
        """Print final statistics."""
        print("\n")  # New line after progress bar
        logger.info("=" * 60)
        logger.info("BACKFILL COMPLETE")
        logger.info("=" * 60)

        total = self.progress.successful + self.progress.failed
        success_rate = (self.progress.successful / total * 100) if total > 0 else 0

        logger.info(f"Total jobs processed: {total}")
        logger.info(f"Successfully classified: {self.progress.successful} ({success_rate:.1f}%)")
        logger.info(f"Failed: {self.progress.failed}")
        logger.info(f"Time elapsed: {self._format_duration(elapsed)}")

        if total > 0:
            rate = total / elapsed
            logger.info(f"Processing rate: {rate:.2f} jobs/second")

        # Show new categories discovered
        if self.category_counter:
            logger.info("-" * 60)
            logger.info("Categories discovered:")
            for category, count in self.category_counter.most_common(20):
                logger.info(f"  {category}: {count}")
            if len(self.category_counter) > 20:
                logger.info(f"  ... and {len(self.category_counter) - 20} more categories")

        logger.info("=" * 60)

    async def run(self) -> dict[str, Any]:
        """Run the category backfill process."""
        global _shutdown_requested

        # Initialize
        if not await self.initialize():
            return {"error": "Failed to initialize classifier"}

        # Handle resume
        if self.resume:
            logger.info("Resuming from previous run...")
            logger.info(f"Previous progress: {self.progress.total_processed} jobs processed")
        elif self.progress.total_processed > 0:
            logger.info(
                "Found existing progress. Use --resume to continue or delete "
                f"{PROGRESS_FILE} to start fresh."
            )
            return {"error": "Existing progress found. Use --resume or delete progress file."}

        self.start_time = time.time()
        self.progress.mark_started()

        batch_num = 0
        last_job_id: UUID | None = None

        if self.resume:
            resume_id = self.progress.get_resume_position()
            if resume_id:
                try:
                    last_job_id = UUID(resume_id)
                    logger.info(f"Resuming after job ID: {last_job_id}")
                except ValueError:
                    logger.warning(f"Invalid resume ID: {resume_id}")

        async with AsyncSessionLocal() as session:
            # Get total count
            total_uncategorized = await self.get_total_uncategorized(session)
            logger.info(f"Found {total_uncategorized} jobs without categories")

            if self.limit:
                total_uncategorized = min(total_uncategorized, self.limit)
                logger.info(f"Processing limited to {total_uncategorized} jobs")

            if self.dry_run:
                logger.info("*** DRY RUN MODE - No changes will be made ***")

            remaining = total_uncategorized

            while remaining > 0 and not _shutdown_requested:
                batch_num += 1
                batch_start = time.time()

                # Fetch batch
                jobs = await self.fetch_batch(session, last_job_id)

                if not jobs:
                    logger.info("No more jobs to process")
                    break

                # Apply limit
                if self.limit:
                    processed_so_far = self.progress.total_processed
                    remaining_limit = self.limit - processed_so_far
                    if remaining_limit <= 0:
                        break
                    jobs = jobs[:remaining_limit]

                # Classify batch
                results = await self.classify_batch(jobs)

                # Extract job ID before session context expires (lazy loading issue)
                batch_last_job_id = jobs[-1].id if jobs else None

                # Update database
                successful, failed, new_categories = await self.update_categories(session, results)

                # Update progress
                last_job_id = batch_last_job_id
                self.progress.update_progress(
                    processed=len(jobs),
                    successful=successful,
                    failed=failed,
                    last_job_id=last_job_id,
                    new_categories=new_categories,
                )

                # Update remaining count
                remaining = await self.get_total_uncategorized(session)
                if self.limit:
                    remaining = min(remaining, self.limit - self.progress.total_processed)

                # Print progress
                batch_time = time.time() - batch_start
                self.print_progress(
                    batch_num=batch_num,
                    batch_success=successful,
                    batch_failed=failed,
                    total_remaining=remaining,
                    batch_time=batch_time,
                )

        # Final stats
        elapsed = time.time() - self.start_time

        if not _shutdown_requested:
            self.progress.mark_completed()
        else:
            logger.warning("\nBackfill interrupted. Progress saved. Run with --resume to continue.")

        self.print_final_stats(elapsed)

        return {
            "total_processed": self.progress.total_processed,
            "successful": self.progress.successful,
            "failed": self.progress.failed,
            "elapsed_seconds": elapsed,
            "categories": dict(self.category_counter),
        }


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Backfill job categories for existing jobs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run full backfill
    uv run python -m pipeline.backfill_categories

    # Test with 100 jobs (dry run)
    uv run python -m pipeline.backfill_categories --limit 100 --dry-run

    # Resume interrupted backfill
    uv run python -m pipeline.backfill_categories --resume

    # Custom batch size
    uv run python -m pipeline.backfill_categories --batch-size 50

    # Reset progress and start fresh
    rm pipeline/.backfill_progress.json
    uv run python -m pipeline.backfill_categories
        """,
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of jobs to process at once (default: 100)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum jobs to process (for testing, default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last processed job",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset progress and start fresh",
    )

    return parser.parse_args()


async def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Set up signal handlers
    setup_signal_handlers()

    # Handle reset
    if args.reset:
        progress = ProgressTracker()
        progress.reset()
        logger.info("Progress reset. Starting fresh backfill...")

    # Create and run backfiller
    backfiller = CategoryBackfiller(
        batch_size=args.batch_size,
        limit=args.limit,
        dry_run=args.dry_run,
        resume=args.resume,
    )

    try:
        result = await backfiller.run()

        if "error" in result:
            logger.error(result["error"])
            return 1

        return 0

    except Exception as e:
        logger.exception(f"Backfill failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
