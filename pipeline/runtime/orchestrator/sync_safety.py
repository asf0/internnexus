"""Sync-safety assessment and stale-job finalization."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.infra.db import AsyncSessionLocal
from pipeline.stages.ingest import IngestResult
from pipeline.domain.sync_result import SYNC_SOURCES
from pipeline.repositories.board_snapshots import mark_bootstrap_complete
from pipeline.repositories.sightings import (
    count_stale_jobs,
    delete_sightings,
    get_previous_successful_source_counts,
    get_sighting_counts,
    prune_abandoned_sightings,
    prune_expired_pipeline_runs,
)
from pipeline.runtime import PipelineStateManager

if TYPE_CHECKING:
    from pipeline.runtime.orchestrator.runner_protocol import RunnerProtocol

    _Base = RunnerProtocol
else:
    _Base = object

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SyncSafetyAssessment:
    safe: bool
    reasons: tuple[str, ...]
    stale_count: int
    source_counts: dict[str, int]
    previous_source_counts: dict[str, int] | None


def _assess_sync_safety(
    ingest: IngestResult,
    *,
    source_counts: dict[str, int],
    previous_source_counts: dict[str, int] | None,
    stale_count: int,
    config,
) -> SyncSafetyAssessment:
    reasons: list[str] = []
    incomplete_sources = sorted(source for source in SYNC_SOURCES if not ingest.source_complete.get(source, False))
    if incomplete_sources:
        reasons.append(f"incomplete sources: {', '.join(incomplete_sources)}")

    current_total = sum(source_counts.values())
    if current_total <= 0:
        reasons.append("current run has no persisted sightings")

    if previous_source_counts:
        previous_total = sum(previous_source_counts.values())
        if previous_total > 0 and current_total < previous_total * config.min_total_sighting_ratio:
            reasons.append(
                f"total sightings {current_total} below {config.min_total_sighting_ratio:.0%} of previous {previous_total}"
            )
        for source, previous_count in previous_source_counts.items():
            current_count = source_counts.get(source, 0)
            if previous_count > 0 and current_count < previous_count * config.min_source_sighting_ratio:
                reasons.append(
                    f"{source} sightings {current_count} below "
                    f"{config.min_source_sighting_ratio:.0%} of previous {previous_count}"
                )

    if stale_count >= config.min_stale_guard_count:
        if current_total <= 0 or current_total / stale_count < config.min_fetched_to_stale_ratio:
            reasons.append(f"sighting/stale ratio is unsafe ({current_total} seen, {stale_count} stale)")

    return SyncSafetyAssessment(
        safe=not reasons,
        reasons=tuple(reasons),
        stale_count=stale_count,
        source_counts=source_counts,
        previous_source_counts=previous_source_counts,
    )


class SyncSafetyMixin(_Base):
    """Guards that must pass before any stale-job mutation runs."""

    async def assess_sync(
        self,
        ingest: IngestResult,
        session: AsyncSession | None = None,
    ) -> SyncSafetyAssessment:
        """Read authoritative counts and reject unsafe synchronization before writes."""

        async def read_inputs(active_session: AsyncSession):
            source_counts = await get_sighting_counts(active_session, ingest.sync_id)
            stale_count = await count_stale_jobs(active_session, ingest.sync_id)
            previous_counts = await get_previous_successful_source_counts(
                active_session,
                exclude_sync_id=ingest.sync_id,
            )
            return source_counts, stale_count, previous_counts

        if session is None:
            async with AsyncSessionLocal() as owned_session:
                source_counts, stale_count, previous_counts = await read_inputs(owned_session)
        else:
            source_counts, stale_count, previous_counts = await read_inputs(session)
        logger.info(
            (
                "Sync safety inputs for %s: current=%s previous=%s stale=%d "
                "complete=%s fetch_errors=%s thresholds="
                "{total_ratio=%.3f, source_ratio=%.3f, stale_guard=%d, "
                "seen_to_stale=%.3f}"
            ),
            ingest.sync_id,
            source_counts,
            previous_counts,
            stale_count,
            ingest.source_complete,
            ingest.fetch_error_counts,
            self.config.sync.min_total_sighting_ratio,
            self.config.sync.min_source_sighting_ratio,
            self.config.sync.min_stale_guard_count,
            self.config.sync.min_fetched_to_stale_ratio,
        )
        assessment = _assess_sync_safety(
            ingest,
            source_counts=source_counts,
            previous_source_counts=previous_counts,
            stale_count=stale_count,
            config=self.config.sync,
        )
        self.results["source_counts"] = source_counts
        self.results["stale_jobs_detected"] = stale_count
        return assessment

    async def cleanup_sync_sightings(
        self,
        sync_id: UUID,
        session: AsyncSession | None = None,
    ) -> None:
        async def cleanup(active_session: AsyncSession) -> tuple[int, int, int]:
            deleted = await delete_sightings(active_session, sync_id)
            pruned = await prune_abandoned_sightings(
                active_session,
                retention_days=self.config.sync.sightings_retention_days,
                batch_size=self.config.sync.sightings_cleanup_batch_size,
            )
            runs_pruned = await prune_expired_pipeline_runs(
                active_session,
                retention_days=self.config.sync.runs_retention_days,
                batch_size=self.config.sync.runs_cleanup_batch_size,
            )
            return deleted, pruned, runs_pruned

        if session is None:
            async with AsyncSessionLocal() as owned_session:
                deleted, pruned, runs_pruned = await cleanup(owned_session)
        else:
            deleted, pruned, runs_pruned = await cleanup(session)
        logger.info(
            "Cleaned %d current and %d abandoned job sightings, %d expired pipeline runs",
            deleted,
            pruned,
            runs_pruned,
        )

    async def finalize_sync(
        self,
        state: PipelineStateManager | None,
        ingest: IngestResult,
    ) -> tuple[int, int]:
        """Finalize legacy bootstrap or acknowledge board-scoped reconciliation."""
        run_session = getattr(state, "session", None)
        if ingest.snapshot_mode:
            if state:
                await state.mark_step_complete(
                    "delete_inactive",
                    {"jobs_marked_inactive": ingest.jobs_deactivated},
                )
            return ingest.jobs_deactivated, 0

        assessment = await self.assess_sync(ingest, session=run_session)
        if not assessment.safe:
            reasons = list(assessment.reasons)
            self.results["sync_skipped_reasons"] = reasons
            logger.error(
                "Skipping all stale-job mutations for sync %s: %s",
                ingest.sync_id,
                "; ".join(reasons),
            )
            if state:
                await state.mark_step_complete(
                    "delete_inactive",
                    {
                        "sync_skipped_reasons": reasons,
                        "stale_jobs_detected": assessment.stale_count,
                        "source_counts": assessment.source_counts,
                    },
                )
            await self.cleanup_sync_sightings(ingest.sync_id, session=run_session)
            return 0, 0

        marked = await self.step_mark_stale_jobs(state, ingest.sync_id)
        await self.cleanup_sync_sightings(ingest.sync_id, session=run_session)

        if ingest.snapshot_bootstrap:
            if run_session is None:
                async with AsyncSessionLocal() as bootstrap_session:
                    await mark_bootstrap_complete(bootstrap_session)
            else:
                await mark_bootstrap_complete(run_session)

        if state:
            await state.mark_step_complete(
                "delete_inactive",
                {"jobs_marked_inactive": marked, "inactive_jobs_deleted": 0},
            )
        return marked, 0
