from __future__ import annotations

import asyncio
import gc
import logging
from types import SimpleNamespace

from pipeline.classification import reset_classifier_async
from pipeline.db import dispose_engines
from pipeline.embeddings.enrichment import reset_embedder
from pipeline.http_client import close_http_client
from pipeline.location.cache import close_location_cache
from pipeline.runtime.commands import claim_next_pending_command, mark_command_completed, mark_command_failed
from pipeline.runtime.sync_lock import job_sync_lock

logger = logging.getLogger(__name__)

# Try to import psutil for memory logging, but make it optional
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def log_memory_usage(label: str = "") -> None:
    """Log current memory usage if psutil is available."""
    if HAS_PSUTIL:
        try:
            process = psutil.Process()
            mem_mb = process.memory_info().rss / 1024 / 1024
            logger.info(f"Memory usage{' (' + label + ')' if label else ''}: {mem_mb:.2f} MB")
        except Exception as e:  # noqa: BLE001  # memory logging is best-effort
            logger.debug(f"Could not log memory usage: {e}")


def trim_process_memory(label: str) -> None:
    """Return freed Python/native heap memory to the OS when possible."""
    gc.collect()

    import ctypes as _ctypes
    import sys as _sys

    if _sys.platform == "linux":
        try:
            _ctypes.CDLL("libc.so.6").malloc_trim(0)
        except Exception:  # noqa: BLE001  # malloc_trim is best-effort memory optimization
            pass

    log_memory_usage(label)


async def cleanup_step_resources(label: str = "") -> None:
    """Release heavyweight per-step resources without disposing DB engines."""
    logger.debug("Cleaning up step resources%s", f" for {label}" if label else "")

    from pipeline.classification import reset_classifier_async
    from pipeline.embeddings.enrichment import reset_embedder

    try:
        await reset_classifier_async()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Error resetting classifier after step: {e}")

    try:
        reset_embedder()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Error resetting embedder after step: {e}")

    trim_process_memory(f"after step cleanup {label}".strip())


async def cleanup_resources() -> None:
    """Clean up global resources to free memory between pipeline runs."""
    logger.debug("Cleaning up resources...")
    log_memory_usage("before cleanup")

    # Close HTTP client connection pool
    try:
        await close_http_client()
        logger.debug("HTTP client closed")
    except Exception as e:  # noqa: BLE001  # cleanup must continue even if one resource fails
        logger.warning(f"Error closing HTTP client: {e}")

    # Close location cache
    try:
        await close_location_cache()
        logger.debug("Location cache closed")
    except Exception as e:  # noqa: BLE001  # cleanup must continue even if one resource fails
        logger.warning(f"Error closing location cache: {e}")

    # Reset classifier singleton (async version)
    try:
        await reset_classifier_async()
        logger.debug("Classifier reset")
    except Exception as e:  # noqa: BLE001  # cleanup must continue even if one resource fails
        logger.warning(f"Error resetting classifier: {e}")

    # Reset embedder singleton
    try:
        reset_embedder()
        logger.debug("Embedder reset")
    except Exception as e:  # noqa: BLE001  # cleanup must continue even if one resource fails
        logger.warning(f"Error resetting embedder: {e}")

    # Dispose database engines
    try:
        await dispose_engines()
        logger.debug("Database engines disposed")
    except Exception as e:  # noqa: BLE001  # cleanup must continue even if one resource fails
        logger.warning(f"Error disposing database engines: {e}")

    # Force garbage collection and return fragmented native heap pages to the OS.
    trim_process_memory("after cleanup")
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


_SYNC_STEPS = {"sync_inactive", "ingest", "delete_inactive"}


async def run_selected_step(runner, args) -> None:
    if args.step == "discover":
        await runner.step_discover(None)
    elif args.step in _SYNC_STEPS:
        async with job_sync_lock():
            if args.step == "sync_inactive":
                await runner.step_sync_inactive(None)
            elif args.step == "ingest":
                await runner.step_ingest(None)
                if args.delete_inactive:
                    await runner.step_delete_inactive(None)
            elif args.step == "delete_inactive":
                await runner.step_delete_inactive(None)
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
    runner.skip_discover = bool(command.skip_discover)
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
            sleep_time = interval * backoff_multiplier
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
        await cleanup_resources()
