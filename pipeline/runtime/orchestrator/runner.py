"""Pipeline runner: run-state, step gating, and top-level orchestration."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any

from pipeline.stages.ingest import IngestResult
from pipeline.runtime import (
    PipelineStateManager,
    get_config,
    get_incomplete_run,
    get_last_completed_run_started_at,
    get_resumable_run,
    mark_unresumable_run_failed,
)
from pipeline.runtime.orchestrator.steps import StepsMixin
from pipeline.runtime.orchestrator.summary import SummaryMixin
from pipeline.runtime.orchestrator.sync_safety import SyncSafetyMixin
from pipeline.runtime.services import cleanup_step_resources
from pipeline.runtime.step_order import PIPELINE_STEPS, get_resume_step
from pipeline.runtime.sync_lock import job_sync_lock, null_sync_lock

logger = logging.getLogger(__name__)


def _empty_results() -> dict[str, Any]:
    """Zeroed result counters for a fresh run."""
    return {
        "jobs_fetched": 0,
        "jobs_changed": 0,
        "source_counts": {},
        "fetch_error_counts": {},
        "source_complete": {},
        "sync_id": None,
        "stale_jobs_detected": 0,
        "locations_cleaned": 0,
        "jobs_classified": 0,
        "classification_errors": 0,
        "embeddings_success": 0,
        "embeddings_errors": 0,
        "jobs_marked_inactive": 0,
        "inactive_jobs_deleted": 0,
    }


def _should_run(step: str, start_from: str | None) -> bool:
    """Whether *step* is at or after the step a resumed run restarts from."""
    if start_from is None:
        return True
    return PIPELINE_STEPS.index(step) >= PIPELINE_STEPS.index(start_from)


class PipelineRunner(StepsMixin, SyncSafetyMixin, SummaryMixin):
    def __init__(
        self,
        dry_run: bool = False,
        process_all: bool = False,
        resume_run_id=None,
        test_mode: bool = False,
        limit: int | None = None,
        state_manager_class=PipelineStateManager,
        get_incomplete_run_func=get_incomplete_run,
        get_resumable_run_func=get_resumable_run,
        get_last_completed_run_started_at_func=get_last_completed_run_started_at,
        classify_commit_batch_size: int | None = None,
        sync_lock_factory=None,
    ):
        self.config = get_config()
        self.dry_run = dry_run
        self.process_all = process_all
        self.resume_run_id = resume_run_id
        self.test_mode = test_mode
        self.limit = limit
        self.state_manager_class = state_manager_class
        self.get_incomplete_run_func = get_incomplete_run_func
        self.get_resumable_run_func = get_resumable_run_func
        self.get_last_completed_run_started_at_func = get_last_completed_run_started_at_func
        self.sync_lock_factory = sync_lock_factory or job_sync_lock
        batch_size = (
            classify_commit_batch_size
            if classify_commit_batch_size is not None
            else self.config.classify.commit_batch_size
        )
        self.classify_commit_batch_size = batch_size
        self._reset_run_state()

    def _reset_run_state(self) -> None:
        """Reset transient state so each run is independent in continuous mode."""
        self.results = _empty_results()
        self.step_times = {}
        self.current_step = None

    async def run(self) -> dict:
        start = time.time()
        self._reset_run_state()

        if self.resume_run_id is not None:
            incomplete_run = await self.get_resumable_run_func(self.resume_run_id)
        else:
            incomplete_run = await self.get_incomplete_run_func()
        start_from_step = None
        resume_run_id = None
        ingest_result: IngestResult | None = None
        if incomplete_run:
            resume_step = get_resume_step(incomplete_run.step_completed)
            if resume_step:
                resume_run_id = incomplete_run.id
                start_from_step = resume_step
                try:
                    resume_metadata = json.loads(getattr(incomplete_run, "results", None) or "{}")
                except (TypeError, json.JSONDecodeError):
                    resume_metadata = {}
                ingest_result = IngestResult.from_metadata(resume_metadata)
                if ingest_result is not None:
                    self.results.update(ingest_result.to_metadata())
                logger.info(
                    "Resuming incomplete run %s from step '%s' (last completed: %s)",
                    incomplete_run.id,
                    start_from_step,
                    incomplete_run.step_completed,
                )
            else:
                reason = f"no valid next step after {incomplete_run.step_completed!r}"
                if not self.dry_run:
                    await mark_unresumable_run_failed(incomplete_run.id, reason)
                logger.warning(
                    "Incomplete run %s failed recovery (%s). Starting a fresh run.",
                    incomplete_run.id,
                    reason,
                )
        elif self.resume_run_id:
            logger.warning(
                "Requested resume run %s but no incomplete run found in DB. Starting fresh.",
                self.resume_run_id,
            )

        state = None

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

            # The sync lock only needs to be held while the steps that mutate
            # job liveness run; delete_inactive is the last of them.
            sync_steps_will_run = _should_run("delete_inactive", start_from_step)
            lock_ctx = self.sync_lock_factory() if sync_steps_will_run else null_sync_lock()

            async with lock_ctx:
                if _should_run("ingest", start_from_step):
                    self.current_step = "ingest"
                    ingest_result = await self.step_ingest(state)
                    self.results["jobs_fetched"] = ingest_result.total_fetched

                if _should_run("delete_inactive", start_from_step):
                    self.current_step = "delete_inactive"
                    if ingest_result is None:
                        reason = "missing persisted ingest synchronization context"
                        logger.error("Skipping all stale-job mutations: %s", reason)
                        self.results["sync_skipped_reasons"] = [reason]
                        if state:
                            await state.mark_step_complete(
                                "delete_inactive",
                                {"sync_skipped_reasons": [reason]},
                            )
                    else:
                        marked, deleted = await self.finalize_sync(state, ingest_result)
                        self.results["jobs_marked_inactive"] = marked
                        self.results["inactive_jobs_deleted"] = deleted

            if _should_run("cleanup", start_from_step):
                self.current_step = "cleanup"
                self.results["locations_cleaned"] = await self.step_cleanup(
                    state, test_mode=self.test_mode, limit=self.limit
                )

            if _should_run("classify", start_from_step):
                self.current_step = "classify"
                try:
                    success, errors = await self.step_classify(state, limit=self.limit)
                    self.results["jobs_classified"] = success
                    self.results["classification_errors"] = errors
                finally:
                    await cleanup_step_resources("classify")

            if _should_run("embed", start_from_step):
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
