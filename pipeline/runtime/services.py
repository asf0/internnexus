from __future__ import annotations

import asyncio
import gc
import logging
import sys
from types import SimpleNamespace

from pipeline.stages.classification import reset_classifier_async
from pipeline.infra.db import dispose_engines
from internnexus_core.http_client import close_http_client
from pipeline.stages.cleanup import close_location_cache
from pipeline.runtime.commands import claim_next_pending_command, mark_command_completed, mark_command_failed
from pipeline.runtime.sync_lock import job_sync_lock

logger = logging.getLogger(__name__)


def trim_process_memory() -> None:
    """Return freed Python/native heap memory to the OS when possible."""
    gc.collect()

    # Lazy: optional platform module used only for Linux malloc trimming.
    import ctypes as _ctypes

    if sys.platform == "linux":
        try:
            _ctypes.CDLL("libc.so.6").malloc_trim(0)
        except Exception:  # noqa: BLE001  # malloc_trim is best-effort memory optimization
            pass


async def cleanup_step_resources(label: str = "") -> None:
    """Release per-step memory without disposing DB engines.

    The classifier singleton is reset by ``step_classify``'s own ``finally``;
    this only returns freed heap pages to the OS between steps.
    """
    logger.debug("Cleaning up step resources%s", f" for {label}" if label else "")
    trim_process_memory()


async def cleanup_resources() -> None:
    """Clean up global resources to free memory between pipeline runs."""
    logger.debug("Cleaning up resources...")

    # Close HTTP client connection pool
    try:
        await close_http_client()
        logger.debug("HTTP client closed")
    except Exception as e:  # noqa: BLE001  # cleanup must continue even if one resource fails
        logger.warning(f"Error closing HTTP client: {e}")

    # Close location cache
    try:
        close_location_cache()
        logger.debug("Location cache closed")
    except Exception as e:  # noqa: BLE001  # cleanup must continue even if one resource fails
        logger.warning(f"Error closing location cache: {e}")

    # Reset classifier singleton (async version)
    try:
        await reset_classifier_async()
        logger.debug("Classifier reset")
    except Exception as e:  # noqa: BLE001  # cleanup must continue even if one resource fails
        logger.warning(f"Error resetting classifier: {e}")

    # Dispose database engines
    try:
        await dispose_engines()
        logger.debug("Database engines disposed")
    except Exception as e:  # noqa: BLE001  # cleanup must continue even if one resource fails
        logger.warning(f"Error disposing database engines: {e}")

    # Force garbage collection and return fragmented native heap pages to the OS.
    trim_process_memory()
    logger.debug("Resource cleanup completed")


async def resolve_resume_run_id(*, resume_requested: bool, get_incomplete_run, logger):
    if not resume_requested:
        return None
    incomplete = await get_incomplete_run()
    if incomplete:
        logger.info(f"Resuming run: {incomplete.id}")
        return incomplete.id
    logger.info("No incomplete run found, starting new run")
    return None


_SYNC_STEPS = {"ingest", "delete_inactive"}


async def run_selected_step(runner, args) -> None:
    if args.step in _SYNC_STEPS:
        async with job_sync_lock():
            if args.step == "ingest":
                ingest = await runner.step_ingest(None)
                if args.delete_inactive:
                    await runner.finalize_sync(None, ingest)
                elif not runner.dry_run and not ingest.snapshot_mode:
                    await runner.cleanup_sync_sightings(ingest.sync_id)
            else:
                raise ValueError("delete_inactive requires run-scoped sightings; use --step ingest --delete-inactive")
    elif args.step == "cleanup":
        await runner.step_cleanup(None, test_mode=args.test, limit=args.limit)
    elif args.step == "classify":
        try:
            await runner.step_classify(None, limit=args.limit)
        finally:
            await cleanup_step_resources("classify")
    elif args.step == "embed":
        try:
            await runner.step_embed(None)
        finally:
            await cleanup_step_resources("embed")


async def run_pipeline_command(runner, command, logger) -> None:
    logger.info("Claimed pipeline command %s (step=%s)", command.id, command.step or "full")
    # command.skip_discover is ignored: the discovery step was retired. The
    # column and its admin-API field still exist and are inert.
    runner.dry_run = bool(command.dry_run)
    runner.process_all = bool(command.process_all)
    runner.test_mode = bool(command.test_mode)
    runner.limit = command.limit
    runner.resume_run_id = None

    try:
        if command.step:
            args = SimpleNamespace(
                step=command.step,
                delete_inactive=False,
                test=bool(command.test_mode),
                limit=command.limit,
            )
            await run_selected_step(runner, args)
            await mark_command_completed(command.id, {"step": command.step})
        else:
            result = await runner.run()
            await mark_command_completed(command.id, result, getattr(runner, "resume_run_id", None))
    except Exception as exc:  # noqa: BLE001  # record command failure, then re-raise
        await mark_command_failed(command.id, exc, getattr(runner, "resume_run_id", None))
        raise


async def run_continuous_loop(*, runner, interval: int, get_incomplete_run, logger) -> None:
    backoff = 1
    while True:
        try:
            command = await claim_next_pending_command()
            if command is not None:
                await run_pipeline_command(runner, command, logger)
            else:
                await runner.run()
            backoff = 1
            runner.resume_run_id = None
            await cleanup_resources()
        except KeyboardInterrupt:
            logger.info("Interrupted, exiting...")
            await cleanup_resources()
            break
        except Exception:  # noqa: BLE001  # continuous loop: any pipeline error triggers backoff
            logger.exception("Pipeline error")
            backoff_multiplier = min(backoff, runner.config.pipeline.max_backoff_multiplier)
            sleep_time = runner.config.pipeline.backoff_on_error * backoff_multiplier
            logger.warning(f"Backing off for {sleep_time}s (multiplier: {backoff_multiplier}x)")
            await cleanup_resources()
            await asyncio.sleep(sleep_time)
            backoff += 1
            incomplete = await get_incomplete_run()
            if incomplete:
                runner.resume_run_id = incomplete.id
            continue

        logger.info(f"Sleeping for {interval}s...")
        await asyncio.sleep(interval)
