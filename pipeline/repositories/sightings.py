"""Queries and retention helpers for run-scoped job sightings."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.ingest.result import SYNC_SOURCES
from pipeline.models import (
    Job,
    JobSource,
    PipelineJobSighting,
    PipelineRun,
    PipelineRunStatus,
)


def _rowcount(result: object) -> int:
    raw = getattr(result, "rowcount", 0)
    return int(raw or 0)


async def get_sighting_counts(session: AsyncSession, sync_id: UUID) -> dict[str, int]:
    result = await session.execute(
        select(PipelineJobSighting.source, func.count())
        .where(PipelineJobSighting.sync_id == sync_id)
        .group_by(PipelineJobSighting.source)
    )
    counts = {source: 0 for source in SYNC_SOURCES}
    for source, count in result.all():
        source_value = source.value if isinstance(source, JobSource) else str(source)
        counts[source_value] = int(count)
    return counts


async def count_stale_jobs(session: AsyncSession, sync_id: UUID) -> int:
    """Count every non-manual row that the synchronization could remove."""
    seen = (
        select(PipelineJobSighting.fingerprint)
        .where(
            PipelineJobSighting.sync_id == sync_id,
            PipelineJobSighting.fingerprint == Job.fingerprint,
        )
        .exists()
    )
    result = await session.execute(
        select(func.count())
        .select_from(Job)
        .where(
            Job.source != JobSource.manual,
            ~seen,
        )
    )
    return int(result.scalar() or 0)


async def get_previous_successful_source_counts(
    session: AsyncSession,
    *,
    exclude_sync_id: UUID,
) -> dict[str, int] | None:
    result = await session.execute(
        select(PipelineRun.results)
        .where(
            PipelineRun.status == PipelineRunStatus.completed,
            PipelineRun.id != exclude_sync_id,
            PipelineRun.results.is_not(None),
        )
        .order_by(PipelineRun.completed_at.desc())
        .limit(20)
    )
    for raw_results in result.scalars():
        try:
            payload = json.loads(raw_results or "{}")
        except (TypeError, json.JSONDecodeError):
            continue
        if payload.get("sync_skipped_reasons"):
            continue
        raw_completeness = payload.get("source_complete")
        if isinstance(raw_completeness, dict) and not all(
            bool(raw_completeness.get(source, False)) for source in SYNC_SOURCES
        ):
            continue
        raw_counts = payload.get("source_counts")
        if isinstance(raw_counts, dict):
            try:
                return {source: int(raw_counts.get(source, 0)) for source in SYNC_SOURCES}
            except (TypeError, ValueError):
                continue
    return None


async def delete_sightings(session: AsyncSession, sync_id: UUID) -> int:
    result = await session.execute(delete(PipelineJobSighting).where(PipelineJobSighting.sync_id == sync_id))
    count = _rowcount(result)
    await session.commit()
    return count


async def prune_abandoned_sightings(
    session: AsyncSession,
    *,
    retention_days: int,
    preserve_sync_id: UUID | None = None,
    batch_size: int = 50_000,
) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, retention_days))
    resumable_runs = select(PipelineRun.id).where(PipelineRun.status == PipelineRunStatus.running)
    total = 0
    batch_size = max(1, batch_size)
    while True:
        candidates = (
            select(
                PipelineJobSighting.sync_id,
                PipelineJobSighting.fingerprint,
            )
            .where(
                PipelineJobSighting.created_at < cutoff,
                PipelineJobSighting.sync_id.not_in(resumable_runs),
            )
            .order_by(
                PipelineJobSighting.created_at,
                PipelineJobSighting.sync_id,
                PipelineJobSighting.fingerprint,
            )
            .limit(batch_size)
        )
        if preserve_sync_id is not None:
            candidates = candidates.where(PipelineJobSighting.sync_id != preserve_sync_id)
        candidate_keys = candidates.cte("expired_sightings")
        result = await session.execute(
            delete(PipelineJobSighting).where(
                tuple_(
                    PipelineJobSighting.sync_id,
                    PipelineJobSighting.fingerprint,
                ).in_(
                    select(
                        candidate_keys.c.sync_id,
                        candidate_keys.c.fingerprint,
                    )
                )
            )
        )
        count = _rowcount(result)
        await session.commit()
        total += count
        if count < batch_size:
            return total
