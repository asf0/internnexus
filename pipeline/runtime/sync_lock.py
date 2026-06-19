"""Advisory lock for the job sync lifecycle.

Uses a PostgreSQL session-level advisory lock pinned to a dedicated
``AsyncConnection`` (not an ``AsyncSession``) to ensure the physical DB
connection is held for the lock's entire lifetime. This prevents the
connection from being returned to the pool while the lock is still held,
and avoids idle-in-transaction state during the long ingest step.

The lock auto-releases if the process or DB connection dies (crash,
SIGTERM), which is the exact scenario that caused the deploy-race
deadlock: the old container's lock releases on death, letting the new
container proceed safely.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text

from pipeline.db import async_engine
from pipeline.repositories.sync_ops import JOB_SYNC_LOCK_KEY

logger = logging.getLogger(__name__)

_LOCK_SQL = text("SELECT pg_advisory_lock(:key)")
_UNLOCK_SQL = text("SELECT pg_advisory_unlock(:key)")


@asynccontextmanager
async def null_sync_lock() -> AsyncIterator[None]:
    """No-op async context manager for conditional lock usage."""
    yield


@asynccontextmanager
async def job_sync_lock() -> AsyncIterator[None]:
    """Acquire a session-level advisory lock for the job sync lifecycle.

    The lock spans sync_inactive -> ingest -> delete_inactive (and the
    rollback/reactivate path). It prevents concurrent pipeline instances
    or overlapping sync operations from deadlocking on the jobs table.

    Uses ``pg_advisory_lock`` (session-level, not transaction-level) on a
    dedicated ``AsyncConnection`` so per-batch commits in the working
    sessions do not release the lock.

    Yields:
        None while the lock is held.

    Raises:
        Any exception from the guarded block is re-raised after the lock
        is released.
    """
    conn = await async_engine.connect()
    try:
        await conn.execute(_LOCK_SQL, {"key": JOB_SYNC_LOCK_KEY})
        await conn.commit()
        logger.info("Acquired job sync advisory lock")
    except Exception:
        await conn.close()
        raise
    try:
        yield
    finally:
        try:
            await conn.execute(_UNLOCK_SQL, {"key": JOB_SYNC_LOCK_KEY})
            await conn.commit()
            logger.info("Released job sync advisory lock")
        except Exception:  # noqa: BLE001  # unlock failure must not mask the original error
            logger.warning("Failed to release job sync advisory lock", exc_info=True)
        finally:
            await conn.close()
