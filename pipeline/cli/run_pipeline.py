#!/usr/bin/env python3
"""
Complete job pipeline: discover companies, fetch jobs, cleanup, and embed.

This script runs the full pipeline:
1. Discover companies - Find company slugs via SearxNG for supported ATS boards
2. Sync inactive - Mark all jobs as inactive (prepare for sync)
3. Fetch & ingest jobs - Fetch from all sources, deduplicate, upsert to DB
4. Delete inactive - Remove jobs not found in APIs (sync model)
5. Cleanup locations - Normalize city/state/country fields
6. Classify jobs - LLM-based category classification
7. Generate embeddings - Create vector embeddings for job matching

Run modes:
  - Full pipeline:    internnexus-pipeline
  - Continuous:       internnexus-pipeline --continuous
  - Single step:      internnexus-pipeline --step discover|sync_inactive|ingest|delete_inactive|cleanup|classify|embed
  - Combined:         internnexus-pipeline --step ingest --delete-inactive
  - Dry run:          internnexus-pipeline --dry-run
  - Resume failed:    internnexus-pipeline --resume
  - Health check:     internnexus-pipeline --check

Examples:
  internnexus-pipeline                                  # Run full pipeline once
  internnexus-pipeline --step ingest                    # Only fetch new jobs
  internnexus-pipeline --step ingest --delete-inactive  # Fetch + delete inactive jobs
  internnexus-pipeline --step sync_inactive             # Mark all jobs as inactive
  internnexus-pipeline --step delete_inactive           # Delete jobs marked as inactive
  internnexus-pipeline --step cleanup                   # Normalize locations
  internnexus-pipeline --step cleanup --all             # Re-process ALL locations
  internnexus-pipeline --step cleanup --test            # Test mode: CSV output only
  internnexus-pipeline --step classify                  # Classify jobs without categories
  internnexus-pipeline --step classify --limit 100      # Classify only 100 jobs
  internnexus-pipeline --step embed                     # Only generate embeddings
  internnexus-pipeline -c                               # Run continuously
  internnexus-pipeline --dry-run                        # Preview without changes
  internnexus-pipeline --resume                         # Resume failed run
  internnexus-pipeline --check                          # Health checks only
"""

from __future__ import annotations

import asyncio
import logging
import sys

from pipeline.cli.args import build_parser
from pipeline.runtime import (
    clear_incomplete_runs,
    get_config,
    get_incomplete_run,
    print_health_report,
    run_health_checks,
)
import pipeline.runtime.runner as _runner_module
from pipeline.runtime import PipelineStateManager
from pipeline.runtime.runner import PipelineRunner as _PipelineRunner
from pipeline.runtime.runner import CLASSIFY_COMMIT_BATCH_SIZE, STEPS as _RUNNER_STEPS
from pipeline.runtime.services import (
    resolve_resume_run_id,
    run_continuous_loop,
    run_selected_step,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
STEPS = _RUNNER_STEPS


class PipelineRunner(_PipelineRunner):
    """Backward-compatible CLI import for the runtime pipeline runner."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.classify_commit_batch_size = CLASSIFY_COMMIT_BATCH_SIZE

    async def run(self) -> dict:
        _runner_module.PipelineStateManager = PipelineStateManager
        _runner_module.get_incomplete_run = get_incomplete_run
        return await super().run()


async def run_continuous(runner: PipelineRunner, interval: int):
    await run_continuous_loop(
        runner=runner,
        interval=interval,
        get_incomplete_run=get_incomplete_run,
        logger=logger,
    )


def main():
    config = get_config()
    parser = build_parser(config)

    args = parser.parse_args()

    interval = args.interval or config.pipeline.continuous_interval

    async def run_once():
        if args.check:
            results = await run_health_checks()
            all_healthy = print_health_report(results)
            if not all_healthy:
                sys.exit(1)
            return

        resume_run_id = await resolve_resume_run_id(
            resume_requested=args.resume,
            get_incomplete_run=get_incomplete_run,
            logger=logger,
        )

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
            await run_selected_step(runner, args)
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
