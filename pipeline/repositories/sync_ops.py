"""Shared batched sync operations for the job sync model.

These helpers implement the mass UPDATE/DELETE operations used by the sync
lifecycle (mark_inactive -> ingest -> delete_inactive / reactivate). They use
CTE-based batched locking with ``ORDER BY id ... FOR UPDATE SKIP LOCKED`` to
ensure deterministic lock ordering, prevent deadlocks, and limit the WAL/lock
footprint of each operation.

All three operations are single-source-of-truth: both ``pipeline/ingest/core.py``
and ``pipeline/repositories/sqlalchemy_repo.py`` delegate here instead of
duplicating SQL.
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.repositories.retry import with_db_retry

logger = logging.getLogger(__name__)

SYNC_BATCH_SIZE = 5000

# Fixed advisory lock key for the job sync lifecycle.
# 0x494E5445524E0001 — "INTER" + sequence; constant across all pipeline instances.
JOB_SYNC_LOCK_KEY = 0x494E5445524E0001

_MARK_INACTIVE_SQL = """
    WITH batch AS (
        SELECT id FROM jobs
        WHERE is_active IS TRUE AND source <> 'manual'::job_source
        ORDER BY id
        FOR UPDATE SKIP LOCKED
        LIMIT :n
    )
    UPDATE jobs SET is_active = false
    FROM batch WHERE jobs.id = batch.id
    RETURNING jobs.id
"""

_REACTIVATE_SQL = """
    WITH batch AS (
        SELECT id FROM jobs
        WHERE is_active IS FALSE AND source <> 'manual'::job_source
        ORDER BY id
        FOR UPDATE SKIP LOCKED
        LIMIT :n
    )
    UPDATE jobs SET is_active = true
    FROM batch WHERE jobs.id = batch.id
    RETURNING jobs.id
"""

_DELETE_INACTIVE_SQL = """
    WITH batch AS (
        SELECT id FROM jobs
        WHERE is_active IS FALSE AND source <> 'manual'::job_source
        ORDER BY id
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
    commit: bool = True,
    batch_size: int = SYNC_BATCH_SIZE,
) -> int:
    """Run a batched CTE sync operation with retry.

    Iterates in id-ordered batches of *batch_size*, committing per batch (when
    *commit* is True) to limit the lock-holding window. Each batch attempt is
    wrapped with ``with_db_retry`` for transient deadlock/serialization errors.

    Args:
        session: SQLAlchemy async session.
        sql: CTE batch SQL template with a ``:n`` parameter for the batch size.
        commit: Whether to commit after each batch.
        batch_size: Number of rows per batch.

    Returns:
        Total number of rows affected across all batches.
    """
    total = 0
    while True:
        async def _batch() -> int:
            result = await session.execute(text(sql), {"n": batch_size})
            rows = result.fetchall()
            if commit:
                await session.commit()
            return len(rows)

        n = await with_db_retry(_batch, rollback=session.rollback)
        total += n
        if n < batch_size:
            break
    return total


async def batched_mark_all_inactive(
    session: AsyncSession,
    *,
    commit: bool = True,
    batch_size: int = SYNC_BATCH_SIZE,
) -> int:
    """Mark all active non-manual jobs as inactive in id-ordered batches.

    Args:
        session: SQLAlchemy async session.
        commit: Whether to commit after each batch.
        batch_size: Number of rows per batch.

    Returns:
        Number of jobs marked inactive.
    """
    total = await _batched_sync_op(session, _MARK_INACTIVE_SQL, commit=commit, batch_size=batch_size)
    if total:
        logger.info("Marked %d jobs as inactive (preparing for sync)", total)
    return total


async def batched_reactivate_inactive(
    session: AsyncSession,
    *,
    commit: bool = True,
    batch_size: int = SYNC_BATCH_SIZE,
) -> int:
    """Reactivate all inactive non-manual jobs in id-ordered batches.

    Rollback helper for the sync model: if a sync run is unsafe, reactivate
    the jobs that were marked inactive.

    Args:
        session: SQLAlchemy async session.
        commit: Whether to commit after each batch.
        batch_size: Number of rows per batch.

    Returns:
        Number of jobs reactivated.
    """
    total = await _batched_sync_op(session, _REACTIVATE_SQL, commit=commit, batch_size=batch_size)
    if total:
        logger.warning("Reactivated %d inactive jobs after unsafe sync guard triggered", total)
    return total


async def batched_delete_inactive(
    session: AsyncSession,
    *,
    commit: bool = True,
    batch_size: int = SYNC_BATCH_SIZE,
) -> int:
    """Delete all inactive non-manual jobs in id-ordered batches.

    After marking all jobs inactive and re-ingesting from APIs, any jobs that
    remain inactive were not found in the APIs and should be deleted.

    Args:
        session: SQLAlchemy async session.
        commit: Whether to commit after each batch.
        batch_size: Number of rows per batch.

    Returns:
        Number of jobs deleted.
    """
    total = await _batched_sync_op(session, _DELETE_INACTIVE_SQL, commit=commit, batch_size=batch_size)
    if total:
        logger.info("Deleted %d inactive jobs (sync model cleanup)", total)
    return total
