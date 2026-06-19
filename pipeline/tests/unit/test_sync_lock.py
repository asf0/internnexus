"""Unit tests for pipeline/runtime/sync_lock.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.repositories.sync_ops import JOB_SYNC_LOCK_KEY


class _FakeConn:
    """Fake AsyncConnection tracking execute/commit/close calls."""

    def __init__(self):
        self.executed: list[tuple[str, dict]] = []
        self.commits = 0
        self.closed = False
        self._fail_unlock = False

    async def execute(self, sql, params=None):
        sql_text = str(sql)
        self.executed.append((sql_text, params or {}))

    async def commit(self):
        self.commits += 1

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_lock_acquires_and_releases():
    conn = _FakeConn()
    fake_engine = MagicMock()
    fake_engine.connect = AsyncMock(return_value=conn)

    with patch("pipeline.runtime.sync_lock.async_engine", fake_engine):
        from pipeline.runtime.sync_lock import job_sync_lock

        async with job_sync_lock():
            assert len(conn.executed) == 1
            assert "pg_advisory_lock" in conn.executed[0][0]
            assert conn.executed[0][1] == {"key": JOB_SYNC_LOCK_KEY}
            assert conn.commits == 1
            assert not conn.closed

        assert len(conn.executed) == 2
        assert "pg_advisory_unlock" in conn.executed[1][0]
        assert conn.commits == 2
        assert conn.closed


@pytest.mark.asyncio
async def test_lock_releases_on_exception():
    conn = _FakeConn()
    fake_engine = MagicMock()
    fake_engine.connect = AsyncMock(return_value=conn)

    with patch("pipeline.runtime.sync_lock.async_engine", fake_engine):
        from pipeline.runtime.sync_lock import job_sync_lock

        with pytest.raises(ValueError, match="boom"):
            async with job_sync_lock():
                raise ValueError("boom")

        assert "pg_advisory_unlock" in conn.executed[-1][0]
        assert conn.closed


@pytest.mark.asyncio
async def test_lock_releases_on_early_return():
    conn = _FakeConn()
    fake_engine = MagicMock()
    fake_engine.connect = AsyncMock(return_value=conn)

    with patch("pipeline.runtime.sync_lock.async_engine", fake_engine):
        from pipeline.runtime.sync_lock import job_sync_lock

        async def _early_return():
            async with job_sync_lock():
                return "result"

        result = await _early_return()
        assert result == "result"
        assert "pg_advisory_unlock" in conn.executed[-1][0]
        assert conn.closed


@pytest.mark.asyncio
async def test_unlock_error_does_not_mask_original_exception():
    conn = _FakeConn()

    original_exc = ValueError("original error")

    async def fail_unlock(sql, params=None):
        if "pg_advisory_unlock" in str(sql):
            raise RuntimeError("unlock failed")

    conn.execute = fail_unlock
    fake_engine = MagicMock()
    fake_engine.connect = AsyncMock(return_value=conn)

    with patch("pipeline.runtime.sync_lock.async_engine", fake_engine):
        from pipeline.runtime.sync_lock import job_sync_lock

        with pytest.raises(ValueError, match="original error"):
            async with job_sync_lock():
                raise original_exc

        assert conn.closed


@pytest.mark.asyncio
async def test_lock_acquire_failure_closes_connection():
    conn = _FakeConn()

    async def fail_lock(sql, params=None):
        raise RuntimeError("connection refused")

    conn.execute = fail_lock
    fake_engine = MagicMock()
    fake_engine.connect = AsyncMock(return_value=conn)

    with patch("pipeline.runtime.sync_lock.async_engine", fake_engine):
        from pipeline.runtime.sync_lock import job_sync_lock

        with pytest.raises(RuntimeError, match="connection refused"):
            async with job_sync_lock():
                pass

        assert conn.closed


@pytest.mark.asyncio
async def test_lock_uses_dedicated_connection_not_session():
    """Verify the lock uses async_engine.connect(), not AsyncSessionLocal()."""
    conn = _FakeConn()
    fake_engine = MagicMock()
    fake_engine.connect = AsyncMock(return_value=conn)

    session_local_calls = []

    class _FakeSessionLocal:
        def __call__(self):
            session_local_calls.append(1)
            raise AssertionError("Should not use AsyncSessionLocal for advisory lock")

    with patch("pipeline.runtime.sync_lock.async_engine", fake_engine):
        from pipeline.runtime.sync_lock import job_sync_lock

        async with job_sync_lock():
            pass

    assert len(session_local_calls) == 0
    assert len(conn.executed) == 2
