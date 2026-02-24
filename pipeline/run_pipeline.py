#!/usr/bin/env python3
"""
Complete job pipeline: discover companies, fetch jobs, cleanup, and embed.

This script runs the full pipeline:
1. Discover companies - Find companies with active Greenhouse/Lever boards
2. Sync inactive - Mark all jobs as inactive (prepare for sync)
3. Fetch & ingest jobs - Fetch from all sources, deduplicate, upsert to DB
4. Delete inactive - Remove jobs not found in APIs (sync model)
5. Cleanup locations - Normalize city/state/country fields
6. Classify jobs - LLM-based category classification
7. Generate embeddings - Create vector embeddings for job matching

Run modes:
  - Full pipeline:    python run_pipeline.py
  - Continuous:       python run_pipeline.py --continuous
  - Single step:      python run_pipeline.py --step discover|sync_inactive|ingest|delete_inactive|cleanup|classify|embed
  - Combined:         python run_pipeline.py --step ingest --delete-inactive
  - Dry run:          python run_pipeline.py --dry-run
  - Resume failed:    python run_pipeline.py --resume
  - Health check:     python run_pipeline.py --check

Examples:
  python run_pipeline.py                                # Run full pipeline once
  python run_pipeline.py --step ingest                  # Only fetch new jobs
  python run_pipeline.py --step ingest --delete-inactive # Fetch + delete inactive jobs
  python run_pipeline.py --step sync_inactive           # Mark all jobs as inactive
  python run_pipeline.py --step delete_inactive         # Delete jobs marked as inactive
  python run_pipeline.py --step cleanup                 # Normalize locations
  python run_pipeline.py --step cleanup --all           # Re-process ALL locations
  python run_pipeline.py --step cleanup --test          # Test mode: CSV output only
  python run_pipeline.py --step classify                # Classify jobs without categories
  python run_pipeline.py --step classify --limit 100    # Classify only 100 jobs
  python run_pipeline.py --step embed                   # Only generate embeddings
  python run_pipeline.py -c                             # Run continuously
  python run_pipeline.py --dry-run                      # Preview without changes
  python run_pipeline.py --resume                       # Resume failed run
  python run_pipeline.py --check                        # Health checks only
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
try:
    from pipeline.path_setup import ensure_project_paths
except ModuleNotFoundError:
    # Support direct script execution from inside pipeline/ directory.
    from path_setup import ensure_project_paths

ensure_project_paths()

from pipeline.fetch import fetch_and_ingest
from pipeline.pipeline import mark_all_jobs_inactive
from pipeline.cleanup import cleanup_locations, delete_inactive_jobs
from pipeline.embeddings import generate_embeddings
from pipeline.health import run_health_checks, print_health_report
from pipeline.pipeline_config import get_config
from pipeline.pipeline_state import (
    PipelineStateManager,
    get_incomplete_run,
    clear_incomplete_runs,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

STEPS = ["discover", "sync_inactive", "ingest", "delete_inactive", "cleanup", "classify", "embed"]


def _log_step_rate(step_name: str, duration_s: float, items: int | None) -> None:
    """Log throughput for count-based steps."""
    if items is None or duration_s <= 0:
        return
    rate = items / duration_s
    logger.info(f"Step '{step_name}' throughput: {rate:.1f} items/sec ({items} items)")


class PipelineRunner:
    def __init__(
        self,
        skip_discover: bool = False,
        dry_run: bool = False,
        process_all: bool = False,
        resume_run_id=None,
        test_mode: bool = False,
        limit: int | None = None,
    ):
        self.config = get_config()
        self.skip_discover = skip_discover
        self.dry_run = dry_run
        self.process_all = process_all
        self.resume_run_id = resume_run_id
        self.test_mode = test_mode
        self.limit = limit
        self.results = {
            "companies_verified": 0,
            "jobs_fetched": 0,
            "locations_cleaned": 0,
            "jobs_classified": 0,
            "classification_errors": 0,
            "embeddings_success": 0,
            "embeddings_errors": 0,
            "jobs_marked_inactive": 0,
            "inactive_jobs_deleted": 0,
        }
        self.step_times = {}
        self.start_from_step = None

    async def run_health_checks(self) -> bool:
        if not self.config.health_check.enabled:
            logger.info("Health checks disabled in config")
            return True

        logger.info("=" * 60)
        logger.info("Running health checks...")
        logger.info("=" * 60)

        results = await run_health_checks()
        all_healthy = print_health_report(results)

        if not all_healthy:
            logger.error("Health checks failed. Use --skip-check to bypass.")
            return False

        logger.info("All health checks passed")
        return True

    async def step_discover(self, state: PipelineStateManager | None) -> int:
        step_start = time.time()
        step_name = "discover"

        if self.dry_run:
            logger.info("[DRY RUN] Would discover companies from browser discovery")
            return 0

        logger.info("Using browser discovery results from pipeline/discovery/output/")
        from pipeline.apis.company_registry import get_all_slugs_by_ats

        slugs = get_all_slugs_by_ats()
        count = sum(len(v) for v in slugs.values())
        self.step_times[step_name] = time.time() - step_start
        logger.info(f"Step 'discover' completed in {self.step_times[step_name]:.1f}s")
        _log_step_rate(step_name, self.step_times[step_name], count)

        if state:
            await state.mark_step_complete(step_name)

        return count

    async def step_ingest(self, state: PipelineStateManager | None) -> tuple[int, datetime]:
        step_start = time.time()
        step_name = "ingest"

        if self.dry_run:
            logger.info("[DRY RUN] Would fetch jobs from APIs and scrapers")
            return 0, datetime.now(timezone.utc)

        jobs_count, batch_start = await fetch_and_ingest(
            api_fetch_concurrency=self.config.api.fetch_concurrency,
            not_found_cooldown_hours=self.config.api.slug_404_cooldown_hours,
        )
        self.step_times[step_name] = time.time() - step_start
        logger.info(f"Step 'ingest' completed in {self.step_times[step_name]:.1f}s")
        _log_step_rate(step_name, self.step_times[step_name], jobs_count)

        if state:
            await state.mark_step_complete(step_name)

        return jobs_count, batch_start

    async def step_cleanup(
        self,
        state: PipelineStateManager | None,
        since=None,
        test_mode: bool = False,
        limit: int | None = None,
    ) -> int:
        step_start = time.time()
        step_name = "cleanup"

        if self.dry_run:
            logger.info("[DRY RUN] Would normalize locations for jobs")
            return 0

        count = await cleanup_locations(
            since=since,
            process_all=self.process_all,
            test_mode=test_mode,
            limit=limit,
            parse_concurrency=self.config.cleanup.parse_concurrency,
            chunk_size=self.config.cleanup.chunk_size,
        )
        self.step_times[step_name] = time.time() - step_start
        logger.info(f"Step 'cleanup' completed in {self.step_times[step_name]:.1f}s")
        _log_step_rate(step_name, self.step_times[step_name], count)

        if state:
            await state.mark_step_complete(step_name)

        return count

    async def step_embed(self, state: PipelineStateManager | None) -> tuple[int, int]:
        step_start = time.time()
        step_name = "embed"

        if self.dry_run:
            logger.info("[DRY RUN] Would generate embeddings for jobs without them")
            return 0, 0

        success, errors = await generate_embeddings(
            batch_size=self.config.embeddings.batch_size,
            parallel_batches=self.config.embeddings.parallel_batches,
        )
        self.step_times[step_name] = time.time() - step_start
        logger.info(f"Step 'embed' completed in {self.step_times[step_name]:.1f}s")
        _log_step_rate(step_name, self.step_times[step_name], success)

        if state:
            await state.mark_step_complete(step_name)

        return success, errors

    async def step_classify(
        self, state: PipelineStateManager | None, limit: int | None = None
    ) -> tuple[int, int]:
        """Classify jobs without categories using LLM."""
        step_start = time.time()
        step_name = "classify"

        if self.dry_run:
            logger.info("[DRY RUN] Would classify jobs without categories")
            return 0, 0

        from pipeline.repositories.sqlalchemy_repo import AsyncSessionLocal, Job
        from sqlalchemy import select
        from pipeline.classification import get_classifier, reset_classifier

        success, errors = 0, 0

        async with AsyncSessionLocal() as session:
            query = (
                select(Job)
                .where(Job.job_category.is_(None))
                .order_by(Job.posted_at.desc().nulls_last())
            )
            if limit:
                query = query.limit(limit)

            result = await session.execute(query)
            jobs = result.scalars().all()

            if not jobs:
                logger.info("No jobs to classify")
                self.step_times[step_name] = time.time() - step_start
                if state:
                    await state.mark_step_complete(step_name)
                return 0, 0

            logger.info(f"Classifying {len(jobs)} jobs without categories...")

            classifier = await get_classifier()
            try:
                inputs = [(j.title, j.description_text or "") for j in jobs]
                categories = await classifier.classify_batch(inputs)

                for job, category in zip(jobs, categories):
                    if category:
                        job.job_category = category
                        success += 1
                    else:
                        errors += 1

                await session.commit()
            finally:
                reset_classifier()

        self.step_times[step_name] = time.time() - step_start
        logger.info(f"Step 'classify' completed in {self.step_times[step_name]:.1f}s")
        _log_step_rate(step_name, self.step_times[step_name], success)

        if state:
            await state.mark_step_complete(step_name)

        return success, errors

    async def step_sync_inactive(self, state: PipelineStateManager | None) -> int:
        """Mark all jobs as inactive before ingestion (sync model)."""
        step_start = time.time()
        step_name = "sync_inactive"

        if self.dry_run:
            logger.info("[DRY RUN] Would mark all jobs as inactive")
            return 0

        from pipeline.repositories.sqlalchemy_repo import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            count = await mark_all_jobs_inactive(session)

        self.step_times[step_name] = time.time() - step_start
        logger.info(f"Step 'sync_inactive' completed in {self.step_times[step_name]:.1f}s")
        _log_step_rate(step_name, self.step_times[step_name], count)

        if state:
            await state.mark_step_complete(step_name)

        return count

    async def step_delete_inactive(self, state: PipelineStateManager | None) -> int:
        """Delete jobs that remain inactive after ingestion (sync model)."""
        step_start = time.time()
        step_name = "delete_inactive"

        if self.dry_run:
            logger.info("[DRY RUN] Would delete inactive jobs")
            return 0

        count = await delete_inactive_jobs()
        self.step_times[step_name] = time.time() - step_start
        logger.info(f"Step 'delete_inactive' completed in {self.step_times[step_name]:.1f}s")
        _log_step_rate(step_name, self.step_times[step_name], count)

        if state:
            await state.mark_step_complete(step_name)

        return count

    async def run(self) -> dict:
        start = time.time()

        incomplete_run = await get_incomplete_run()
        if incomplete_run and not self.resume_run_id:
            logger.warning(f"Found incomplete run: {incomplete_run.id}")
            logger.warning(f"  Started: {incomplete_run.started_at}")
            logger.warning(f"  Last completed step: {incomplete_run.step_completed}")
            logger.warning("Use --resume to continue or --fresh to start new")
            return self.results

        state = None
        batch_start_time = None

        if not self.dry_run:
            state = PipelineStateManager(run_id=self.resume_run_id)
            await state.__aenter__()
            await state.start_run()

            if self.resume_run_id and incomplete_run:
                self.start_from_step = state.get_resume_step(incomplete_run)
                if self.start_from_step:
                    logger.info(f"Resuming from step: {self.start_from_step}")

        try:
            logger.info("=" * 60)
            logger.info(f"PIPELINE START - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            if self.dry_run:
                logger.info("*** DRY RUN MODE - No changes will be made ***")
            logger.info("=" * 60)

            if not self.start_from_step or self.start_from_step == "discover":
                if not self.skip_discover:
                    self.results["companies_verified"] = await self.step_discover(state)
                elif state:
                    await state.mark_step_complete("discover")

            if not self.start_from_step or STEPS.index("sync_inactive") >= STEPS.index(
                self.start_from_step or "sync_inactive"
            ):
                self.results["jobs_marked_inactive"] = await self.step_sync_inactive(state)

            if not self.start_from_step or STEPS.index("ingest") >= STEPS.index(
                self.start_from_step or "ingest"
            ):
                jobs_count, batch_start_time = await self.step_ingest(state)
                self.results["jobs_fetched"] = jobs_count

            if not self.start_from_step or STEPS.index("delete_inactive") >= STEPS.index(
                self.start_from_step or "delete_inactive"
            ):
                self.results["inactive_jobs_deleted"] = await self.step_delete_inactive(state)

            if not self.start_from_step or STEPS.index("cleanup") >= STEPS.index(
                self.start_from_step or "cleanup"
            ):
                self.results["locations_cleaned"] = await self.step_cleanup(
                    state, test_mode=self.test_mode, limit=self.limit
                )

            if not self.start_from_step or STEPS.index("classify") >= STEPS.index(
                self.start_from_step or "classify"
            ):
                success, errors = await self.step_classify(state, limit=self.limit)
                self.results["jobs_classified"] = success
                self.results["classification_errors"] = errors

            if not self.start_from_step or STEPS.index("embed") >= STEPS.index(
                self.start_from_step or "embed"
            ):
                success, errors = await self.step_embed(state)
                self.results["embeddings_success"] = success
                self.results["embeddings_errors"] = errors

            if state:
                await state.mark_completed(self.results)

            elapsed = time.time() - start
            self._log_summary(elapsed)

        except Exception as e:
            current_step = STEPS[0]
            for i, step in enumerate(STEPS):
                if step in self.step_times:
                    if i + 1 < len(STEPS):
                        current_step = STEPS[i + 1]
            if state:
                await state.mark_failed(e, current_step)
            raise
        finally:
            if state:
                await state.__aexit__(None, None, None)

        return self.results

    def _log_summary(self, elapsed: float):
        logger.info("=" * 60)
        logger.info(f"PIPELINE COMPLETE - {elapsed:.1f}s ({elapsed / 60:.1f} min)")
        logger.info("=" * 60)
        logger.info("Results:")
        logger.info(f"  Companies verified: {self.results['companies_verified']}")
        logger.info(f"  Jobs fetched: {self.results['jobs_fetched']}")
        logger.info(f"  Locations cleaned: {self.results['locations_cleaned']}")
        logger.info(f"  Jobs classified: {self.results['jobs_classified']}")
        logger.info(f"  Classification errors: {self.results['classification_errors']}")
        logger.info(f"  Embeddings generated: {self.results['embeddings_success']}")
        logger.info(f"  Embedding errors: {self.results['embeddings_errors']}")
        logger.info(f"  Jobs marked inactive: {self.results['jobs_marked_inactive']}")
        logger.info(f"  Inactive jobs deleted: {self.results['inactive_jobs_deleted']}")
        logger.info("-" * 60)
        logger.info("Step timings:")
        for step, duration in self.step_times.items():
            logger.info(f"  {step}: {duration:.1f}s")
        logger.info("=" * 60)


async def run_continuous(runner: PipelineRunner, interval: int):
    backoff = 1

    while True:
        try:
            await runner.run()
            backoff = 1
            runner.resume_run_id = None
        except KeyboardInterrupt:
            logger.info("Interrupted, exiting...")
            break
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            backoff_multiplier = min(backoff, runner.config.pipeline.max_backoff_multiplier)
            sleep_time = interval * backoff_multiplier
            logger.warning(f"Backing off for {sleep_time}s (multiplier: {backoff_multiplier}x)")
            await asyncio.sleep(sleep_time)
            backoff += 1
            incomplete = await get_incomplete_run()
            if incomplete:
                runner.resume_run_id = incomplete.id
            continue

        logger.info(f"Sleeping for {interval}s...")
        await asyncio.sleep(interval)


def main():
    config = get_config()

    parser = argparse.ArgumentParser(
        description="Run job ingestion pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_pipeline.py                      # Run full pipeline once
  python run_pipeline.py -c                   # Run continuously (every hour by default)
  python run_pipeline.py -c --interval 3600   # Run continuously every hour
  python run_pipeline.py --step ingest        # Only fetch new jobs  
  python run_pipeline.py --step ingest --delete-inactive  # Fetch + delete inactive
  python run_pipeline.py --step sync_inactive # Mark all jobs inactive
  python run_pipeline.py --step delete_inactive # Delete inactive jobs
  python run_pipeline.py --step embed         # Only generate embeddings
  python run_pipeline.py --dry-run            # Preview without changes
  python run_pipeline.py --resume             # Resume failed run
  python run_pipeline.py --check              # Health checks only
  python run_pipeline.py --step cleanup --all # Re-process ALL locations
  python run_pipeline.py --step cleanup --test # Test mode: CSV output only
        """,
    )
    parser.add_argument("--continuous", "-c", action="store_true", help="Run continuously")
    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=None,
        help=f"Interval in seconds (default: {config.pipeline.continuous_interval})",
    )
    parser.add_argument(
        "--step",
        choices=[
            "discover",
            "sync_inactive",
            "ingest",
            "delete_inactive",
            "cleanup",
            "classify",
            "embed",
        ],
        help="Run only a specific step",
    )
    parser.add_argument(
        "--delete-inactive",
        action="store_true",
        help="With --step ingest, also delete inactive jobs after ingestion",
    )
    parser.add_argument("--skip-discover", action="store_true", help="Skip company discovery")
    parser.add_argument(
        "--all",
        action="store_true",
        help="With --step cleanup, re-process ALL jobs",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    parser.add_argument("--check", action="store_true", help="Run health checks only")
    parser.add_argument("--skip-check", action="store_true", help="Skip health checks")
    parser.add_argument("--resume", action="store_true", help="Resume from last failed run")
    parser.add_argument("--fresh", action="store_true", help="Start fresh (clear incomplete runs)")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode for cleanup: write results to CSV without DB changes",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit number of jobs to process (for --test mode)"
    )

    args = parser.parse_args()

    interval = args.interval or config.pipeline.continuous_interval

    async def run_once():
        if args.check:
            results = await run_health_checks()
            if not results:
                sys.exit(1)
            return

        resume_run_id = None
        if args.resume:
            incomplete = await get_incomplete_run()
            if incomplete:
                resume_run_id = incomplete.id
                logger.info(f"Resuming run: {resume_run_id}")
            else:
                logger.info("No incomplete run found, starting new run")

        runner = PipelineRunner(
            skip_discover=args.skip_discover,
            dry_run=args.dry_run,
            process_all=args.all,
            resume_run_id=resume_run_id,
            test_mode=args.test,
            limit=args.limit,
        )

        if not args.skip_check and not args.dry_run and not args.test:
            healthy = await runner.run_health_checks()
            if not healthy:
                sys.exit(1)

        if args.step:
            if args.step == "discover":
                await runner.step_discover(None)
            elif args.step == "sync_inactive":
                await runner.step_sync_inactive(None)
            elif args.step == "ingest":
                await runner.step_ingest(None)
                if args.delete_inactive:
                    await runner.step_delete_inactive(None)
            elif args.step == "delete_inactive":
                await runner.step_delete_inactive(None)
            elif args.step == "cleanup":
                await runner.step_cleanup(None, test_mode=args.test)
            elif args.step == "classify":
                await runner.step_classify(None, limit=args.limit)
            elif args.step == "embed":
                await runner.step_embed(None)
        else:
            if args.fresh:
                cleared = await clear_incomplete_runs()
                if cleared:
                    logger.info(f"Cleared {cleared} incomplete run(s)")
            await runner.run()

    if args.continuous:

        async def run_continuous_main():
            resume_run_id = None
            incomplete = await get_incomplete_run()
            if incomplete:
                resume_run_id = incomplete.id
                logger.info(f"Resuming incomplete run: {resume_run_id}")

            runner = PipelineRunner(
                skip_discover=args.skip_discover,
                dry_run=args.dry_run,
                process_all=args.all,
                resume_run_id=resume_run_id,
                test_mode=args.test,
                limit=args.limit,
            )
            logger.info(f"Starting continuous pipeline (interval: {interval}s)")
            await run_continuous(runner, interval)

        asyncio.run(run_continuous_main())
    else:
        asyncio.run(run_once())


if __name__ == "__main__":
    main()
