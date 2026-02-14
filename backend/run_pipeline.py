#!/usr/bin/env python3
"""
Complete job pipeline: discover companies, fetch jobs, cleanup, and embed.

This script runs the full pipeline:
1. Discover companies - Find companies with active Greenhouse/Lever boards
2. Fetch & ingest jobs - Fetch from all sources, deduplicate, upsert to DB
3. Cleanup locations - Normalize city/state/country fields
4. Generate embeddings - Create vector embeddings for job matching
5. Delete old jobs - Remove jobs not seen in X days

Run modes:
  - Full pipeline:    python run_pipeline.py
  - Continuous:       python run_pipeline.py --continuous
  - Single step:      python run_pipeline.py --step discover|ingest|cleanup|embed
  - Dry run:          python run_pipeline.py --dry-run
  - Resume failed:    python run_pipeline.py --resume
  - Health check:     python run_pipeline.py --check

Examples:
  python run_pipeline.py                      # Run full pipeline once
  python run_pipeline.py --step ingest        # Only fetch new jobs
  python run_pipeline.py --step embed         # Only generate embeddings
  python run_pipeline.py -c                   # Run continuously (uses config interval)
  python run_pipeline.py --dry-run            # Preview what would happen
  python run_pipeline.py --resume             # Resume from last failed step
  python run_pipeline.py --check              # Run health checks only
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ingestion.discovery import discover_companies
from ingestion.fetch import fetch_and_ingest
from ingestion.cleanup import cleanup_locations, delete_old_jobs
from ingestion.embeddings import generate_embeddings
from ingestion.health import run_health_checks, print_health_report
from ingestion.pipeline_config import get_config
from ingestion.pipeline_state import (
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

STEPS = ["discover", "ingest", "cleanup", "embed", "delete_old"]


class PipelineRunner:
    def __init__(
        self,
        skip_discover: bool = False,
        dry_run: bool = False,
        process_all: bool = False,
        resume_run_id=None,
    ):
        self.config = get_config()
        self.skip_discover = skip_discover
        self.dry_run = dry_run
        self.process_all = process_all
        self.resume_run_id = resume_run_id
        self.results = {
            "companies_verified": 0,
            "jobs_fetched": 0,
            "locations_cleaned": 0,
            "embeddings_success": 0,
            "embeddings_errors": 0,
            "old_jobs_deleted": 0,
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
            logger.info("[DRY RUN] Would discover companies from Simplify.jobs")
            return 0

        companies = await discover_companies()
        count = len(companies)
        self.step_times[step_name] = time.time() - step_start
        logger.info(f"Step 'discover' completed in {self.step_times[step_name]:.1f}s")

        if state:
            await state.mark_step_complete(step_name)

        return count

    async def step_ingest(self, state: PipelineStateManager | None) -> tuple[int, datetime]:
        step_start = time.time()
        step_name = "ingest"

        if self.dry_run:
            logger.info("[DRY RUN] Would fetch jobs from APIs and scrapers")
            return 0, datetime.now(timezone.utc)

        jobs_count, batch_start = await fetch_and_ingest()
        self.step_times[step_name] = time.time() - step_start
        logger.info(f"Step 'ingest' completed in {self.step_times[step_name]:.1f}s")

        if state:
            await state.mark_step_complete(step_name)

        return jobs_count, batch_start

    async def step_cleanup(self, state: PipelineStateManager | None, since=None) -> int:
        step_start = time.time()
        step_name = "cleanup"

        if self.dry_run:
            logger.info("[DRY RUN] Would normalize locations for jobs")
            return 0

        count = await cleanup_locations(since=since, process_all=self.process_all)
        self.step_times[step_name] = time.time() - step_start
        logger.info(f"Step 'cleanup' completed in {self.step_times[step_name]:.1f}s")

        if state:
            await state.mark_step_complete(step_name)

        return count

    async def step_embed(self, state: PipelineStateManager | None) -> tuple[int, int]:
        step_start = time.time()
        step_name = "embed"

        if self.dry_run:
            logger.info("[DRY RUN] Would generate embeddings for jobs without them")
            return 0, 0

        success, errors = await generate_embeddings(batch_size=self.config.embeddings.batch_size)
        self.step_times[step_name] = time.time() - step_start
        logger.info(f"Step 'embed' completed in {self.step_times[step_name]:.1f}s")

        if state:
            await state.mark_step_complete(step_name)

        return success, errors

    async def step_delete_old(self, state: PipelineStateManager | None) -> int:
        step_start = time.time()
        step_name = "delete_old"

        if self.dry_run:
            logger.info(
                f"[DRY RUN] Would delete jobs older than {self.config.pipeline.delete_after_days} days"
            )
            return 0

        count = await delete_old_jobs(days=self.config.pipeline.delete_after_days)
        self.step_times[step_name] = time.time() - step_start
        logger.info(f"Step 'delete_old' completed in {self.step_times[step_name]:.1f}s")

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

            if not self.start_from_step or STEPS.index("ingest") >= STEPS.index(
                self.start_from_step or "ingest"
            ):
                jobs_count, batch_start_time = await self.step_ingest(state)
                self.results["jobs_fetched"] = jobs_count

            if not self.start_from_step or STEPS.index("cleanup") >= STEPS.index(
                self.start_from_step or "cleanup"
            ):
                self.results["locations_cleaned"] = await self.step_cleanup(state)

            if not self.start_from_step or STEPS.index("embed") >= STEPS.index(
                self.start_from_step or "embed"
            ):
                success, errors = await self.step_embed(state)
                self.results["embeddings_success"] = success
                self.results["embeddings_errors"] = errors

            if not self.start_from_step or STEPS.index("delete_old") >= STEPS.index(
                self.start_from_step or "delete_old"
            ):
                self.results["old_jobs_deleted"] = await self.step_delete_old(state)

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
        logger.info(f"  Embeddings generated: {self.results['embeddings_success']}")
        logger.info(f"  Embedding errors: {self.results['embeddings_errors']}")
        logger.info(f"  Old jobs deleted: {self.results['old_jobs_deleted']}")
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
  python run_pipeline.py                      # Run full pipeline
  python run_pipeline.py --step ingest        # Only fetch new jobs  
  python run_pipeline.py --step embed         # Only generate embeddings
  python run_pipeline.py -c                   # Run continuously
  python run_pipeline.py --dry-run            # Preview without changes
  python run_pipeline.py --resume             # Resume failed run
  python run_pipeline.py --check              # Health checks only
  python run_pipeline.py --step cleanup --all # Re-process ALL locations
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
        choices=["discover", "ingest", "cleanup", "embed"],
        help="Run only a specific step",
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
        )

        if not args.skip_check and not args.dry_run:
            healthy = await runner.run_health_checks()
            if not healthy:
                sys.exit(1)

        if args.step:
            if args.step == "discover":
                await runner.step_discover(None)
            elif args.step == "ingest":
                await runner.step_ingest(None)
            elif args.step == "cleanup":
                await runner.step_cleanup(None)
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
            )
            logger.info(f"Starting continuous pipeline (interval: {interval}s)")
            await run_continuous(runner, interval)

        asyncio.run(run_continuous_main())
    else:
        asyncio.run(run_once())


if __name__ == "__main__":
    main()
