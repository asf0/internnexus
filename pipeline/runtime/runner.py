"""Pipeline runner implementation used by the CLI and continuous runtime."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from pipeline.cleanup import cleanup_locations, delete_inactive_jobs
from pipeline.embeddings import generate_embeddings
from pipeline.ingest import fetch_and_ingest, mark_stale_jobs_inactive, reactivate_inactive_jobs
from pipeline.runtime import (
    PipelineStateManager,
    get_config,
    get_incomplete_run,
    print_health_report,
    run_health_checks,
)
from pipeline.runtime.services import cleanup_step_resources, log_memory_usage, trim_process_memory
from pipeline.runtime.steps import PIPELINE_STEPS
from pipeline.runtime.sync_lock import job_sync_lock, null_sync_lock

logger = logging.getLogger(__name__)

CLASSIFY_COMMIT_BATCH_SIZE = 200
MIN_MARKED_INACTIVE_FOR_DELETE_GUARD = 1000
MIN_FETCHED_TO_MARKED_INACTIVE_RATIO = 0.5
STEPS = PIPELINE_STEPS


def _log_step_rate(step_name: str, duration_s: float, items: int | None) -> None:
    """Log throughput for count-based steps."""
    if items is None or duration_s <= 0:
        return
    rate = items / duration_s
    logger.info(f"Step '{step_name}' throughput: {rate:.1f} items/sec ({items} items)")


def _get_resume_step_from_db_run(step_completed: str | None) -> str | None:
    """Return the next step name for a DB run's completed step."""
    if not step_completed:
        return PIPELINE_STEPS[0]
    try:
        idx = PIPELINE_STEPS.index(step_completed)
    except ValueError:
        return None
    if idx < len(PIPELINE_STEPS) - 1:
        return PIPELINE_STEPS[idx + 1]
    return None


def _is_unsafe_delete_inactive_sync(marked_inactive: int, jobs_fetched: int) -> bool:
    """Return True when ingest looks too incomplete to drive hard deletes."""
    if marked_inactive <= 0:
        return False
    if jobs_fetched <= 0:
        return True
    if marked_inactive < MIN_MARKED_INACTIVE_FOR_DELETE_GUARD:
        return False
    return jobs_fetched / marked_inactive < MIN_FETCHED_TO_MARKED_INACTIVE_RATIO


class PipelineRunner:
    def __init__(
        self,
        skip_discover: bool = False,
        dry_run: bool = False,
        process_all: bool = False,
        resume_run_id=None,
        test_mode: bool = False,
        limit: int | None = None,
        state_manager_class=PipelineStateManager,
        get_incomplete_run_func=get_incomplete_run,
        classify_commit_batch_size: int = CLASSIFY_COMMIT_BATCH_SIZE,
    ):
        self.config = get_config()
        self.skip_discover = skip_discover
        self.dry_run = dry_run
        self.process_all = process_all
        self.resume_run_id = resume_run_id
        self.test_mode = test_mode
        self.limit = limit
        self.state_manager_class = state_manager_class
        self.get_incomplete_run_func = get_incomplete_run_func
        self.classify_commit_batch_size = classify_commit_batch_size
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
        self.current_step: str | None = None

    def _reset_run_state(self) -> None:
        """Reset transient state so each run is independent in continuous mode."""
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
        self.current_step = None

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
            logger.info("[DRY RUN] Would discover companies via SearxNG")
            return 0

        from pipeline.discovery import discover_companies

        logger.info("Running company discovery via SearxNG")
        slugs = await discover_companies()
        count = sum(len(values) for values in slugs.values())
        self.step_times[step_name] = time.time() - step_start
        logger.info(f"Step 'discover' completed in {self.step_times[step_name]:.1f}s")
        _log_step_rate(step_name, self.step_times[step_name], count)

        if state:
            await state.mark_step_complete(step_name)

        log_memory_usage("after discovery")
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
            slug_chunk_size=self.config.ingest.slug_chunk_size,
            upsert_batch_size=self.config.ingest.upsert_batch_size,
            run_id=str(state.run_id) if state is not None and state.run_id is not None else None,
        )
        self.step_times[step_name] = time.time() - step_start
        logger.info(f"Step 'ingest' completed in {self.step_times[step_name]:.1f}s")
        _log_step_rate(step_name, self.step_times[step_name], jobs_count)

        if state:
            await state.mark_step_complete(step_name)

        log_memory_usage("after ingest")
        trim_process_memory("after ingest trim")
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
            location_cache_max_size=self.config.cleanup.location_cache_max_size,
        )
        self.step_times[step_name] = time.time() - step_start
        logger.info(f"Step 'cleanup' completed in {self.step_times[step_name]:.1f}s")
        _log_step_rate(step_name, self.step_times[step_name], count)

        if state:
            await state.mark_step_complete(step_name)

        log_memory_usage("after location cleanup")
        trim_process_memory("after location cleanup trim")
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

        log_memory_usage("after embed")

        return success, errors

    async def step_classify(self, state: PipelineStateManager | None, limit: int | None = None) -> tuple[int, int]:
        """Classify jobs without categories using LLM."""
        step_start = time.time()
        step_name = "classify"

        if self.dry_run:
            logger.info("[DRY RUN] Would classify jobs without categories")
            return 0, 0

        from sqlalchemy import func, select, update

        from pipeline.classification import get_classifier, reset_classifier_async
        from pipeline.repositories.sqlalchemy_repo import AsyncSessionLocal, Job

        success, errors = 0, 0

        async with AsyncSessionLocal() as session:
            total_query = select(func.count()).select_from(Job).where(Job.job_category.is_(None))
            total_result = await session.execute(total_query)
            total_available = int(total_result.scalar() or 0)
            total_jobs = min(limit, total_available) if limit else total_available

            if total_jobs == 0:
                logger.info("No jobs to classify")
                self.step_times[step_name] = time.time() - step_start
                if state:
                    await state.mark_step_complete(step_name)
                return 0, 0

            logger.info("Classifying %d jobs without categories...", total_jobs)

            classifier = get_classifier()
            processed = 0
            attempted_job_ids: set[object] = set()
            try:
                while processed < total_jobs:
                    batch_limit = min(self.classify_commit_batch_size, total_jobs - processed)
                    batch_query = (
                        select(Job.id, Job.title, Job.description_text)
                        .where(Job.job_category.is_(None))
                        .order_by(
                            Job.posted_at.desc().nulls_last(),
                            Job.id.desc(),
                        )
                        .limit(batch_limit)
                    )
                    if attempted_job_ids:
                        batch_query = batch_query.where(Job.id.notin_(attempted_job_ids))
                    batch_result = await session.execute(batch_query)
                    rows = batch_result.all()
                    if not rows:
                        logger.warning(
                            "Classification stopped early at %d/%d jobs; no uncategorized rows returned after excluding %d attempted rows",
                            processed,
                            total_jobs,
                            len(attempted_job_ids),
                        )
                        break

                    inputs = [(row.title, row.description_text or "") for row in rows]
                    # inputs = [(j.title, j.description_text or "") for j in chunk]
                    categories_with_reason = await classifier.classify_batch_with_reasons(inputs)

                    batch_success = 0
                    batch_errors = 0
                    failed_entries: list[tuple[object | None, str]] = []
                    for row, (category, reason) in zip(rows, categories_with_reason):
                        if category:
                            await session.execute(update(Job).where(Job.id == row.id).values(job_category=category))
                            success += 1
                            batch_success += 1
                        else:
                            # Only track failures — they stay NULL and could re-appear in the query
                            if row.id is not None:
                                attempted_job_ids.add(row.id)
                                failed_entries.append((row.id, reason))
                            errors += 1
                            batch_errors += 1

                    if failed_entries:
                        sample = ", ".join(f"{job_id}:{reason}" for job_id, reason in failed_entries[:10])
                        logger.warning(
                            "Classification failed for %d jobs in batch (sample: %s)",
                            len(failed_entries),
                            sample,
                        )

                    await session.commit()
                    session.expunge_all()  # free Job ORM objects (incl. description_text) immediately
                    processed += len(rows)
                    batch_success_rate = (batch_success / len(rows)) * 100 if rows else 0.0
                    cumulative_success_rate = (success / processed) * 100 if processed else 0.0
                    logger.info(
                        (
                            "Classification commit progress: %d/%d "
                            "(batch_success=%d, batch_errors=%d, batch_success_rate=%.1f%%; "
                            "success=%d, errors=%d, cumulative_success_rate=%.1f%%)"
                        ),
                        processed,
                        total_jobs,
                        batch_success,
                        batch_errors,
                        batch_success_rate,
                        success,
                        errors,
                        cumulative_success_rate,
                    )
            finally:
                await reset_classifier_async()

        self.step_times[step_name] = time.time() - step_start
        logger.info(f"Step 'classify' completed in {self.step_times[step_name]:.1f}s")
        _log_step_rate(step_name, self.step_times[step_name], success)

        if state:
            await state.mark_step_complete(step_name)

        log_memory_usage("after classify")

        return success, errors

    async def step_sync_inactive(self, state: PipelineStateManager | None) -> int:
        """No-op in the last_seen sync model; kept for resume compatibility."""
        step_start = time.time()
        step_name = "sync_inactive"

        if self.dry_run:
            logger.info("[DRY RUN] Would mark all jobs as inactive")
            return 0

        logger.info("sync_inactive is deprecated; using last_seen sync model")
        count = 0

        self.step_times[step_name] = time.time() - step_start
        logger.info(f"Step 'sync_inactive' completed in {self.step_times[step_name]:.1f}s")
        _log_step_rate(step_name, self.step_times[step_name], count)

        if state:
            await state.mark_step_complete(step_name)

        return count

    async def step_mark_stale_jobs(
        self,
        state: PipelineStateManager | None,
        batch_start_time: datetime,
    ) -> int:
        """Mark jobs that were not seen this run as inactive."""
        step_start = time.time()
        step_name = "mark_stale_jobs"

        if self.dry_run:
            logger.info("[DRY RUN] Would mark stale jobs as inactive")
            return 0

        from pipeline.repositories.sqlalchemy_repo import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            logger.info("Marking stale jobs inactive (last_seen < %s)...", batch_start_time.isoformat())
            count = await mark_stale_jobs_inactive(session, batch_start_time)
            logger.info("Marked %d stale jobs as inactive", count)

        self.step_times[step_name] = time.time() - step_start
        logger.info(f"Step 'mark_stale_jobs' completed in {self.step_times[step_name]:.1f}s")
        _log_step_rate(step_name, self.step_times[step_name], count)

        if state:
            await state.mark_step_complete(step_name)

        return count

    async def step_delete_inactive(
        self,
        state: PipelineStateManager | None,
        batch_start_time: datetime,
    ) -> int:
        """Delete jobs that remain inactive after ingestion (sync model)."""
        step_start = time.time()
        step_name = "delete_inactive"

        if self.dry_run:
            logger.info("[DRY RUN] Would delete inactive jobs")
            return 0

        count = await delete_inactive_jobs(batch_start_time=batch_start_time)
        self.step_times[step_name] = time.time() - step_start
        logger.info(f"Step 'delete_inactive' completed in {self.step_times[step_name]:.1f}s")
        _log_step_rate(step_name, self.step_times[step_name], count)

        if state:
            await state.mark_step_complete(step_name)

        return count

    async def rollback_sync_inactive(self) -> int:
        """Reactivate jobs when a sync run is not safe enough to delete from."""
        from pipeline.repositories.sqlalchemy_repo import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            return await reactivate_inactive_jobs(session)

    async def run(self) -> dict:
        start = time.time()
        self._reset_run_state()

        incomplete_run = await self.get_incomplete_run_func()
        start_from_step = None
        resume_run_id = None
        if incomplete_run:
            resume_step = _get_resume_step_from_db_run(incomplete_run.step_completed)
            if resume_step:
                resume_run_id = incomplete_run.id
                start_from_step = resume_step
                logger.info(
                    "Resuming incomplete run %s from step '%s' (last completed: %s)",
                    incomplete_run.id,
                    start_from_step,
                    incomplete_run.step_completed,
                )
            else:
                logger.warning(
                    "Incomplete run %s has no resumable next step (last completed: %s). Starting a fresh run.",
                    incomplete_run.id,
                    incomplete_run.step_completed,
                )
        elif self.resume_run_id:
            logger.warning(
                "Requested resume run %s but no incomplete run found in DB. Starting fresh.",
                self.resume_run_id,
            )

        state = None
        batch_start_time = None

        if not self.dry_run:
            state = self.state_manager_class(run_id=resume_run_id)
            await state.__aenter__()
            await state.start_run()

        try:
            logger.info("=" * 60)
            logger.info(f"PIPELINE START - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            if self.dry_run:
                logger.info("*** DRY RUN MODE - No changes will be made ***")
            logger.info("=" * 60)

            if not start_from_step or start_from_step == "discover":
                self.current_step = "discover"
                if not self.skip_discover:
                    self.results["companies_verified"] = await self.step_discover(state)
                elif state:
                    await state.mark_step_complete("discover")
            sync_steps_will_run = start_from_step is None or PIPELINE_STEPS.index(
                start_from_step
            ) <= PIPELINE_STEPS.index("delete_inactive")
            lock_ctx = job_sync_lock() if sync_steps_will_run else null_sync_lock()

            async with lock_ctx:
                if not start_from_step or PIPELINE_STEPS.index("sync_inactive") >= PIPELINE_STEPS.index(
                    start_from_step or "sync_inactive"
                ):
                    self.current_step = "sync_inactive"
                    # Deprecated: no-op in last_seen sync model.
                    await self.step_sync_inactive(state)

                if not start_from_step or PIPELINE_STEPS.index("ingest") >= PIPELINE_STEPS.index(
                    start_from_step or "ingest"
                ):
                    self.current_step = "ingest"
                    jobs_count, batch_start_time = await self.step_ingest(state)
                    self.results["jobs_fetched"] = jobs_count

                if not start_from_step or PIPELINE_STEPS.index("delete_inactive") >= PIPELINE_STEPS.index(
                    start_from_step or "delete_inactive"
                ):
                    self.current_step = "delete_inactive"

                    # Mark stale jobs inactive before deletion. Skip if we are
                    # resuming from a point after ingestion already ran.
                    if not start_from_step or PIPELINE_STEPS.index("ingest") >= PIPELINE_STEPS.index(
                        start_from_step or "ingest"
                    ):
                        if batch_start_time is None:
                            raise RuntimeError("Cannot mark stale jobs without an ingest batch start time")
                        self.results["jobs_marked_inactive"] = await self.step_mark_stale_jobs(state, batch_start_time)

                    missing_sync_context = (
                        start_from_step in {"ingest", "delete_inactive"} and self.results["jobs_marked_inactive"] == 0
                    )
                    unsafe_partial_sync = _is_unsafe_delete_inactive_sync(
                        self.results["jobs_marked_inactive"],
                        self.results["jobs_fetched"],
                    )
                    if missing_sync_context or unsafe_partial_sync:
                        logger.error(
                            (
                                "Skipping delete_inactive because the sync is unsafe "
                                "(start_from_step=%s, fetched=%d, marked_inactive=%d). "
                                "Reactivating inactive jobs to avoid a destructive partial sync."
                            ),
                            start_from_step,
                            self.results["jobs_fetched"],
                            self.results["jobs_marked_inactive"],
                        )
                        await self.rollback_sync_inactive()
                        if state:
                            await state.mark_step_complete("delete_inactive")
                        self.results["inactive_jobs_deleted"] = 0
                    else:
                        if batch_start_time is None:
                            raise RuntimeError("Cannot delete inactive jobs without an ingest batch start time")
                        self.results["inactive_jobs_deleted"] = await self.step_delete_inactive(state, batch_start_time)

            if not start_from_step or PIPELINE_STEPS.index("cleanup") >= PIPELINE_STEPS.index(
                start_from_step or "cleanup"
            ):
                self.current_step = "cleanup"
                self.results["locations_cleaned"] = await self.step_cleanup(
                    state, test_mode=self.test_mode, limit=self.limit
                )

            if not start_from_step or PIPELINE_STEPS.index("classify") >= PIPELINE_STEPS.index(
                start_from_step or "classify"
            ):
                self.current_step = "classify"
                try:
                    success, errors = await self.step_classify(state, limit=self.limit)
                    self.results["jobs_classified"] = success
                    self.results["classification_errors"] = errors
                finally:
                    await cleanup_step_resources("classify")

            if not start_from_step or PIPELINE_STEPS.index("embed") >= PIPELINE_STEPS.index(start_from_step or "embed"):
                self.current_step = "embed"
                try:
                    success, errors = await self.step_embed(state)
                    self.results["embeddings_success"] = success
                    self.results["embeddings_errors"] = errors
                finally:
                    await cleanup_step_resources("embed")

            if state:
                await state.mark_completed(self.results)
            self.current_step = None

            elapsed = time.time() - start
            self._log_summary(elapsed)

        except Exception as e:  # noqa: BLE001  # top-level run guard: record step failure, then re-raise
            current_step = self.current_step or PIPELINE_STEPS[0]
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
