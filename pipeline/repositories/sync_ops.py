"""Shared batched sync operations for the job sync model.

These helpers implement the mass UPDATE/DELETE operations used by the sync
lifecycle (ingest -> mark_stale -> delete_inactive / reactivate). They use
CTE-based batched locking with ``ORDER BY id ... FOR UPDATE SKIP LOCKED`` to
ensure deterministic lock ordering, prevent deadlocks, and limit the WAL/lock
footprint of each operation.

All three operations are single-source-of-truth: both ``pipeline/ingest/core.py``
and ``pipeline/repositories/sqlalchemy_repo.py`` delegate here instead of
duplicating SQL.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.repositories.retry import with_db_retry

logger = logging.getLogger(__name__)

SYNC_BATCH_SIZE = 5000

# Fixed advisory lock key for the job sync lifecycle.
# 0x494E5445524E0001 — "INTER" + sequence; constant across all pipeline instances.
JOB_SYNC_LOCK_KEY = 0x494E5445524E0001

_MARK_STALE_SQL = """
    WITH batch AS (
        SELECT jobs.id FROM jobs
        WHERE jobs.is_active IS TRUE
          AND jobs.source <> 'manual'::job_source
          AND NOT EXISTS (
              SELECT 1 FROM pipeline_job_sightings sightings
              WHERE sightings.sync_id = :sync_id
                AND sightings.fingerprint = jobs.fingerprint
          )
        ORDER BY jobs.id
        FOR UPDATE SKIP LOCKED
        LIMIT :n
    )
    UPDATE jobs SET is_active = false
    FROM batch WHERE jobs.id = batch.id
    RETURNING jobs.id
"""

_DELETE_INACTIVE_SQL = """
    WITH batch AS (
        SELECT jobs.id FROM jobs
        WHERE jobs.is_active IS FALSE
          AND jobs.source <> 'manual'::job_source
          AND NOT EXISTS (
              SELECT 1 FROM pipeline_job_sightings sightings
              WHERE sightings.sync_id = :sync_id
                AND sightings.fingerprint = jobs.fingerprint
          )
        ORDER BY jobs.id
        FOR UPDATE SKIP LOCKED
        LIMIT :n
    )
    DELETE FROM jobs USING batch
    WHERE jobs.id = batch.id
    RETURNING jobs.id
"""


async def _batched_sync_op(
    session: AsyncSession,
    sql: str,
    *,
    params: dict | None = None,
    commit: bool = True,
    batch_size: int = SYNC_BATCH_SIZE,
    max_attempts: int | None = None,
    base_delay: float | None = None,
    max_delay: float | None = None,
) -> int:
    """Run a batched CTE sync operation with retry.

    Iterates in id-ordered batches of *batch_size*, committing per batch (when
    *commit* is True) to limit the lock-holding window. Each batch attempt is
    wrapped with ``with_db_retry`` for transient deadlock/serialization errors.

    Args:
        session: SQLAlchemy async session.
        sql: CTE batch SQL template with a ``:n`` parameter for the batch size.
        params: Optional additional parameters passed to every batch execution.
        commit: Whether to commit after each batch.
        batch_size: Number of rows per batch.

    Returns:
        Total number of rows affected across all batches.
    """
    params = params or {}
    total = 0
    while True:

        async def _batch() -> int:
            result = await session.execute(
                text(sql),
                {"n": batch_size, **params},
            )
            rows = result.fetchall()
            if commit:
                await session.commit()
            return len(rows)

        n = await with_db_retry(
            _batch,
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            rollback=session.rollback,
        )
        total += n
        if n < batch_size:
            break
    return total


async def batched_mark_stale_jobs_inactive(
    session: AsyncSession,
    sync_id: UUID,
    *,
    commit: bool = True,
    batch_size: int = SYNC_BATCH_SIZE,
    max_attempts: int | None = None,
    base_delay: float | None = None,
    max_delay: float | None = None,
) -> int:
    """Mark active non-manual jobs that were not seen this run as inactive.

    Uses absence from the run-scoped sightings table to identify stale jobs.

    Args:
        session: SQLAlchemy async session.
        sync_id: Synchronization run whose sightings define active jobs.
        commit: Whether to commit after each batch.
        batch_size: Number of rows per batch.

    Returns:
        Number of jobs marked inactive.
    """
    total = await _batched_sync_op(
        session,
        _MARK_STALE_SQL,
        params={"sync_id": sync_id},
        commit=commit,
        batch_size=batch_size,
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
    )
    if total:
        logger.info("Marked %d jobs absent from sync %s as inactive", total, sync_id)
    return total


async def batched_delete_inactive(
    session: AsyncSession,
    sync_id: UUID,
    *,
    commit: bool = True,
    batch_size: int = SYNC_BATCH_SIZE,
    max_attempts: int | None = None,
    base_delay: float | None = None,
    max_delay: float | None = None,
) -> int:
    """Delete inactive non-manual jobs that were not seen this run.

    Args:
        session: SQLAlchemy async session.
        sync_id: Synchronization run whose sightings define retained jobs.
        commit: Whether to commit after each batch.
        batch_size: Number of rows per batch.

    Returns:
        Number of jobs deleted.
    """
    total = await _batched_sync_op(
        session,
        _DELETE_INACTIVE_SQL,
        params={"sync_id": sync_id},
        commit=commit,
        batch_size=batch_size,
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
    )
    if total:
        logger.info("Deleted %d inactive jobs (sync model cleanup)", total)
    return total
