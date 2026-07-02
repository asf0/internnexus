"""Unit tests for pipeline/repositories/sync_ops.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import DBAPIError

from pipeline.repositories import sync_ops
from pipeline.repositories.sync_ops import (
    JOB_SYNC_LOCK_KEY,
    SYNC_BATCH_SIZE,
    _batched_sync_op,
    batched_delete_inactive,
    batched_mark_stale_jobs_inactive,
)
from pipeline.runtime.config import SyncConfig


class _FakeResult:
    """Fake execute result returning a configurable number of rows."""

    def __init__(self, row_count: int):
        self._rows = [object() for _ in range(row_count)]

    def fetchall(self):
        return list(self._rows)


class _FakeSession:
    """Fake async session that tracks execute/commit/rollback calls."""

    def __init__(self, batch_counts: list[int], fail_first_with: Exception | None = None):
        self._batch_counts = list(batch_counts)
        self._call_index = 0
        self._fail_first_with = fail_first_with
        self.executed_sql: list[str] = []
        self.executed_params: list[dict] = []
        self.commits = 0
        self.rollbacks = 0

    async def execute(self, statement, params=None):
        sql_text = str(statement)
        self.executed_sql.append(sql_text)
        self.executed_params.append(params or {})
        if self._fail_first_with is not None and self._call_index == 0:
            self._call_index += 1
            raise self._fail_first_with
        idx = min(self._call_index, len(self._batch_counts) - 1)
        count = self._batch_counts[idx]
        self._call_index += 1
        return _FakeResult(count)

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


def _make_dbapi_error(pgcode: str = "40P01") -> DBAPIError:
    from pipeline.tests.unit.test_db_retry import _make_dbapi_error as _mk

    return _mk(pgcode)


class TestBatchedSyncOp:
    @pytest.mark.asyncio
    async def test_single_batch_when_under_limit(self):
        session = _FakeSession([100])
        total = await _batched_sync_op(session, "SELECT 1", batch_size=5000)
        assert total == 100
        assert len(session.executed_sql) == 1
        assert session.commits == 1

    @pytest.mark.asyncio
    async def test_multi_batch_when_exceeding_limit(self):
        session = _FakeSession([5000, 5000, 100])
        total = await _batched_sync_op(session, "SELECT 1", batch_size=5000)
        assert total == 10100
        assert len(session.executed_sql) == 3
        assert session.commits == 3

    @pytest.mark.asyncio
    async def test_no_commit_when_commit_false(self):
        session = _FakeSession([10])
        await _batched_sync_op(session, "SELECT 1", commit=False)
        assert session.commits == 0

    @pytest.mark.asyncio
    async def test_retry_on_deadlock_then_completes(self):
        deadlock_exc = _make_dbapi_error("40P01")
        session = _FakeSession([5000, 100], fail_first_with=deadlock_exc)
        total = await _batched_sync_op(session, "SELECT 1", batch_size=5000)
        assert session.rollbacks == 1
        assert total == 100

    @pytest.mark.asyncio
    async def test_empty_table_returns_zero(self):
        session = _FakeSession([0])
        total = await _batched_sync_op(session, "SELECT 1")
        assert total == 0
        assert len(session.executed_sql) == 1

    @pytest.mark.asyncio
    async def test_batch_size_param_passed(self):
        session = _FakeSession([10])
        await _batched_sync_op(session, "SELECT 1", batch_size=5000)
        assert session.executed_params[0] == {"n": 5000}

    @pytest.mark.asyncio
    async def test_configured_batch_size_is_threaded_to_each_batch(self):
        config = SyncConfig(sync_batch_size=100)
        session = _FakeSession([100, 40])

        total = await _batched_sync_op(
            session,
            "SELECT 1",
            batch_size=config.sync_batch_size,
        )

        assert total == 140
        assert session.executed_params == [{"n": 100}, {"n": 100}]

    @pytest.mark.asyncio
    async def test_extra_params_passed_through(self):
        from datetime import datetime, timezone

        session = _FakeSession([10])
        batch_start = datetime.now(timezone.utc)
        await _batched_sync_op(session, "SELECT 1", params={"batch_start_time": batch_start})
        assert session.executed_params[0] == {"n": 5000, "batch_start_time": batch_start}


class TestBatchedMarkStaleInactive:
    @pytest.mark.asyncio
    async def test_delegates_with_correct_sql(self):
        session = _FakeSession([10])
        sync_id = uuid4()
        total = await batched_mark_stale_jobs_inactive(session, sync_id)
        assert total == 10
        sql = session.executed_sql[0]
        assert "is_active IS TRUE" in sql
        assert "source <> 'manual'" in sql
        assert "pipeline_job_sightings" in sql
        assert "sightings.sync_id = :sync_id" in sql
        assert "sightings.fingerprint = jobs.fingerprint" in sql
        assert "FOR UPDATE SKIP LOCKED" in sql
        assert "UPDATE jobs SET is_active = false" in sql

    @pytest.mark.asyncio
    async def test_no_log_when_zero(self):
        session = _FakeSession([0])
        await batched_mark_stale_jobs_inactive(session, uuid4())


class TestBatchedDeleteInactive:
    @pytest.mark.asyncio
    async def test_delegates_with_correct_sql(self):
        session = _FakeSession([30])
        sync_id = uuid4()
        total = await batched_delete_inactive(session, sync_id)
        assert total == 30
        sql = session.executed_sql[0]
        assert "is_active IS FALSE" in sql
        assert "pipeline_job_sightings" in sql
        assert "sightings.sync_id = :sync_id" in sql
        assert "DELETE FROM jobs" in sql
        assert "FOR UPDATE SKIP LOCKED" in sql


class TestConstants:
    def test_batch_size_is_5000(self):
        assert SYNC_BATCH_SIZE == 5000

    def test_lock_key_is_nonzero_constant(self):
        assert JOB_SYNC_LOCK_KEY == 0x494E5445524E0001

    def test_sql_templates_use_skip_locked_and_order_by(self):
        for sql in [
            sync_ops._MARK_STALE_SQL,
            sync_ops._DELETE_INACTIVE_SQL,
        ]:
            assert "FOR UPDATE SKIP LOCKED" in sql
            assert "ORDER BY" in sql
            assert "source <> 'manual'" in sql
