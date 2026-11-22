"""Per-step execution methods for :class:`PipelineRunner`."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pipeline.stages.classification import get_classifier, reset_classifier_async
from pipeline.stages.cleanup import cleanup_locations
from pipeline.infra.db import AsyncSessionLocal
from pipeline.stages.embeddings import generate_embeddings
from pipeline.stages.ingest import IngestResult, fetch_and_ingest, mark_stale_jobs_inactive
from pipeline.runtime import PipelineStateManager, run_and_report_health
from pipeline.runtime.classify_step import run_classify_step
from pipeline.runtime.orchestrator.summary import _log_step_rate
from pipeline.runtime.services import trim_process_memory

if TYPE_CHECKING:
    from pipeline.runtime.orchestrator.runner_protocol import RunnerProtocol

    _Base = RunnerProtocol
else:
    _Base = object

logger = logging.getLogger(__name__)


class StepsMixin(_Base):
    """Individual pipeline steps, each timed and state-tracked."""

    async def run_health_checks(self) -> bool:
        if not self.config.health_check.enabled:
            logger.info("Health checks disabled in config")
            return True

        logger.info("=" * 60)
        logger.info("Running health checks...")
        logger.info("=" * 60)

        all_healthy = await run_and_report_health()

        if not all_healthy:
            logger.error("Health checks failed. Use --skip-check to bypass.")
            return False

        logger.info("All health checks passed")
        return True

    async def step_ingest(self, state: PipelineStateManager | None) -> IngestResult:
        step_start = time.time()
        step_name = "ingest"

        if self.dry_run:
            logger.info("[DRY RUN] Would fetch jobs from APIs and scrapers")
            return IngestResult.empty(uuid4())

        try:
            sync_id = UUID(str(state.run_id)) if state is not None and state.run_id is not None else uuid4()
        except ValueError:
            sync_id = uuid4()

        result = await fetch_and_ingest(
            api_fetch_concurrency=self.config.api.fetch_concurrency,
            not_found_cooldown_hours=self.config.api.slug_404_cooldown_hours,
            slug_chunk_size=self.config.ingest.slug_chunk_size,
            upsert_batch_size=self.config.ingest.upsert_batch_size,
            sync_id=sync_id,
        )
        self.step_times[step_name] = time.time() - step_start
        logger.info(f"Step 'ingest' completed in {self.step_times[step_name]:.1f}s")
        _log_step_rate(step_name, self.step_times[step_name], result.total_fetched)

        self.results.update(result.to_metadata())

        if state:
            await state.mark_step_complete(step_name, result.to_metadata())

        trim_process_memory()
        return result

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

        # Bound the raw normalization UPDATEs to rows seen since the last
        # completed run; unscoped they re-scan the entire jobs table every
        # cycle. `--process-all` still forces a full pass.
        normalize_since = None
        if since is None and not self.process_all:
            normalize_since = await self.get_last_completed_run_started_at_func()
            if normalize_since is not None:
                logger.info(f"Scoping raw location normalization to jobs seen since {normalize_since}")

        count = await cleanup_locations(
            since=since,
            normalize_since=normalize_since,
            process_all=self.process_all,
            test_mode=test_mode,
            limit=limit,
            parse_concurrency=self.config.cleanup.parse_concurrency,
            chunk_size=self.config.cleanup.chunk_size,
            location_cache_max_size=self.config.cleanup.location_cache_max_size,
            warm_batch=self.config.cleanup.warm_batch,
        )
        self.step_times[step_name] = time.time() - step_start
        logger.info(f"Step 'cleanup' completed in {self.step_times[step_name]:.1f}s")
        _log_step_rate(step_name, self.step_times[step_name], count)

        if state:
            await state.mark_step_complete(step_name)

        trim_process_memory()
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

    async def step_classify(self, state: PipelineStateManager | None, limit: int | None = None) -> tuple[int, int]:
        """Classify jobs without categories using LLM."""
        step_start = time.time()
        step_name = "classify"

        if self.dry_run:
            logger.info("[DRY RUN] Would classify jobs without categories")
            return 0, 0

        async with AsyncSessionLocal() as db:
            classifier = get_classifier()
            try:
                result = await run_classify_step(
                    db=db,
                    classifier=classifier,
                    commit_batch_size=self.classify_commit_batch_size,
                    limit=limit,
                )
            finally:
                await reset_classifier_async()

        self.step_times[step_name] = time.time() - step_start
        logger.info(f"Step 'classify' completed in {self.step_times[step_name]:.1f}s")
        _log_step_rate(step_name, self.step_times[step_name], result.success_count)

        if state:
            await state.mark_step_complete(step_name)

        return result.success_count, result.error_count

    async def step_mark_stale_jobs(
        self,
        state: PipelineStateManager | None,
        sync_id: UUID,
    ) -> int:
        """Mark jobs that were not seen this run as inactive."""
        step_start = time.time()
        step_name = "mark_stale_jobs"

        if self.dry_run:
            logger.info("[DRY RUN] Would mark stale jobs as inactive")
            return 0

        batch_size = self.config.sync.sync_batch_size
        retry_options = self.config.retry

        async with AsyncSessionLocal() as session:
            logger.info("Marking jobs absent from sync %s inactive...", sync_id)
            count = await mark_stale_jobs_inactive(
                session,
                sync_id,
                batch_size=batch_size,
                max_attempts=retry_options.db_max_attempts,
                base_delay=retry_options.db_base_delay_seconds,
                max_delay=retry_options.db_max_delay_seconds,
            )
            logger.info("Marked %d stale jobs as inactive", count)

        self.step_times[step_name] = time.time() - step_start
        logger.info(f"Step 'mark_stale_jobs' completed in {self.step_times[step_name]:.1f}s")
        _log_step_rate(step_name, self.step_times[step_name], count)

        return count
