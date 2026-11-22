#!/usr/bin/env python3
"""
Complete job pipeline: fetch jobs, cleanup, classify, and embed.

This script runs the full pipeline:
1. Ingest - Record sightings and upsert changed jobs
2. Delete inactive - Remove jobs absent from completed sightings
3. Cleanup locations - Normalize city/state/country fields
4. Classify jobs - LLM-based category classification
5. Generate embeddings - Create vector embeddings for job matching

Run modes:
  - Full pipeline:    internnexus-pipeline
  - Continuous:       internnexus-pipeline --continuous
  - Single step:      internnexus-pipeline --step ingest|cleanup|classify|embed
  - Combined:         internnexus-pipeline --step ingest --delete-inactive
  - Dry run:          internnexus-pipeline --dry-run
  - Resume failed:    internnexus-pipeline --resume
  - Health check:     internnexus-pipeline --check

Examples:
  internnexus-pipeline                                  # Run full pipeline once
  internnexus-pipeline --step ingest                    # Only fetch new jobs
  internnexus-pipeline --step ingest --delete-inactive  # Fetch + delete stale jobs
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
from pipeline.infra.logging_config import configure_logging
from pipeline.runtime import (
    clear_incomplete_runs,
    get_config,
    get_incomplete_run,
    get_resumable_run,
    run_and_report_health,
)
from pipeline.runtime.orchestrator import PipelineRunner as _RuntimePipelineRunner
from pipeline.runtime.services import (
    resolve_resume_run_id,
    run_continuous_loop,
    run_selected_step,
)

configure_logging()
logger = logging.getLogger(__name__)


async def run_continuous(runner: _RuntimePipelineRunner, interval: int):
    await run_continuous_loop(
        runner=runner,
        interval=interval,
        get_incomplete_run=get_resumable_run,
        logger=logger,
    )


def _build_runner(args, resume_run_id) -> _RuntimePipelineRunner:
    return _RuntimePipelineRunner(
        dry_run=args.dry_run,
        process_all=args.all,
        resume_run_id=resume_run_id,
        test_mode=args.test,
        limit=args.limit,
    )


async def _exit_if_unhealthy(runner: _RuntimePipelineRunner, args) -> None:
    if not args.skip_check and not args.dry_run and not args.test:
        healthy = await runner.run_health_checks()
        if not healthy:
            sys.exit(1)


async def _run_once(args) -> None:
    if args.check:
        if not await run_and_report_health():
            sys.exit(1)
        return

    resume_run_id = await resolve_resume_run_id(
        resume_requested=args.resume,
        get_incomplete_run=get_resumable_run,
        logger=logger,
    )

    runner = _build_runner(args, resume_run_id)
    await _exit_if_unhealthy(runner, args)

    if args.step:
        await run_selected_step(runner, args)
        return

    if args.fresh:
        cleared = await clear_incomplete_runs()
        if cleared:
            logger.info(f"Cleared {cleared} incomplete run(s)")
    await runner.run()


async def _run_continuous_main(args, interval: int) -> None:
    resume_run_id = await resolve_resume_run_id(
        resume_requested=True,
        get_incomplete_run=get_incomplete_run,
        logger=logger,
    )

    runner = _build_runner(args, resume_run_id)
    await _exit_if_unhealthy(runner, args)
    logger.info(f"Starting continuous pipeline (interval: {interval}s)")
    await run_continuous(runner, interval)


def main():
    config = get_config()
    parser = build_parser(config)

    args = parser.parse_args()

    interval = args.interval or config.pipeline.continuous_interval

    if args.continuous:
        asyncio.run(_run_continuous_main(args, interval))
    else:
        asyncio.run(_run_once(args))


if __name__ == "__main__":
    main()
