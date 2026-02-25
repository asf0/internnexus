from __future__ import annotations

import asyncio


async def resolve_resume_run_id(*, resume_requested: bool, get_incomplete_run, logger):
    if not resume_requested:
        return None
    incomplete = await get_incomplete_run()
    if incomplete:
        logger.info(f"Resuming run: {incomplete.id}")
        return incomplete.id
    logger.info("No incomplete run found, starting new run")
    return None


async def run_selected_step(runner, args) -> None:
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
        await runner.step_cleanup(None, test_mode=args.test, limit=args.limit)
    elif args.step == "classify":
        await runner.step_classify(None, limit=args.limit)
    elif args.step == "embed":
        await runner.step_embed(None)


async def run_continuous_loop(*, runner, interval: int, get_incomplete_run, logger) -> None:
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
