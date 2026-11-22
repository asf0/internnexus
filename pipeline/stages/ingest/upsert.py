"""Changed-only job upserts with atomic run-scoped sighting records."""

from __future__ import annotations

import asyncio
import gc
import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.domain import JobSchema
from pipeline.repositories.job_upsert import build_job_rows, changed_only_job_upsert
from pipeline.stages.ingest.deduplication import deduplicate_jobs
from pipeline.infra.models import PipelineJobSighting
from pipeline.infra.job_cache import invalidate_job_detail_cache
from pipeline.infra.pipeline_config import get_config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UpsertStats:
    seen: int = 0
    changed: int = 0

    def __add__(self, other: UpsertStats) -> UpsertStats:
        return UpsertStats(seen=self.seen + other.seen, changed=self.changed + other.changed)


async def upsert_jobs(
    db: AsyncSession,
    jobs: list[JobSchema],
    *,
    sync_id: UUID,
    deduplicate: bool = True,
    batch_size: int | None = None,
) -> UpsertStats:
    """Record sightings and upsert only new, changed, or reactivated jobs."""
    if not jobs:
        return UpsertStats()

    if batch_size is None:
        batch_size = get_config().ingest.upsert_batch_size

    unique_jobs = deduplicate_jobs(jobs) if deduplicate else jobs
    if deduplicate and len(unique_jobs) < len(jobs):
        logger.info("Deduped %d jobs within batch", len(jobs) - len(unique_jobs))
    totals = UpsertStats()
    for i in range(0, len(unique_jobs), batch_size):
        batch = unique_jobs[i : i + batch_size]
        rows, sighting_rows = build_job_rows(batch)
        for sighting in sighting_rows:
            sighting["sync_id"] = sync_id

        sightings_stmt = (
            insert(PipelineJobSighting)
            .values(sighting_rows)
            .on_conflict_do_nothing(
                index_elements=[
                    PipelineJobSighting.sync_id,
                    PipelineJobSighting.fingerprint,
                ]
            )
        )
        try:
            await db.execute(sightings_stmt)
            result = await db.execute(changed_only_job_upsert(rows))
            changed_ids = [row[0] for row in result.fetchall()]
            changed = len(changed_ids)
            await db.commit()
        except Exception:
            await db.rollback()
            raise

        await invalidate_job_detail_cache(changed_ids)

        db.expunge_all()
        await asyncio.sleep(0)
        totals += UpsertStats(seen=len(rows), changed=changed)
        logger.info(
            "Upserted batch %d: seen=%d changed=%d unchanged=%d",
            i // batch_size + 1,
            len(rows),
            changed,
            len(rows) - changed,
        )

        if (i // batch_size + 1) % 10 == 0:
            gc.collect()

    return totals
