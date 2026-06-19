"""Unit tests for pipeline/repositories/retry.py."""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy.exc import DBAPIError

from pipeline.repositories.retry import (
    RETRYABLE_SQLSTATES,
    _retryable_sqlstate,
    with_db_retry,
)


class _FakeDriverError(Exception):
    """Simulates an asyncpg driver error carrying pgcode."""

    def __init__(self, pgcode: str | None = None, message: str = "db error"):
        super().__init__(message)
        self.pgcode = pgcode


def _make_dbapi_error(pgcode: str | None = "40P01") -> DBAPIError:
    """Build a SQLAlchemy DBAPIError wrapping a fake driver error."""
    orig = _FakeDriverError(pgcode=pgcode)
    return DBAPIError.instance(
        statement=None,
        params=None,
        orig=orig,
        dbapi_base_err=Exception,
    )


class TestRetryableSqlstate:
    def test_detects_pgcode_on_orig(self):
        exc = _make_dbapi_error("40P01")
        assert _retryable_sqlstate(exc) == "40P01"

    def test_detects_sqlstate_attr(self):
        err = _FakeDriverError()
        err.sqlstate = "40001"
        delattr(err, "pgcode")
        exc = DBAPIError.instance(None, None, err, Exception)
        assert _retryable_sqlstate(exc) == "40001"

    def test_walks_cause_chain(self):
        deep = _FakeDriverError(pgcode="55P03")
        mid = ValueError("middle")
        mid.__cause__ = deep
        exc = DBAPIError.instance(None, None, mid, Exception)
        assert _retryable_sqlstate(exc) == "55P03"

    def test_returns_none_for_non_retryable(self):
        exc = _make_dbapi_error("23505")
        assert _retryable_sqlstate(exc) is None

    def test_returns_none_when_no_code(self):
        exc = _make_dbapi_error(None)
        assert _retryable_sqlstate(exc) is None

    def test_avoids_infinite_cycle(self):
        err = _FakeDriverError(pgcode="40P01")
        err.__cause__ = err  # self-referential cycle
        assert _retryable_sqlstate(err) == "40P01"

    def test_all_expected_codes_in_set(self):
        assert RETRYABLE_SQLSTATES == frozenset({"40P01", "40001", "55P03"})


class TestWithDbRetry:
    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        calls = 0

        async def func():
            nonlocal calls
            calls += 1
            return "ok"

        result = await with_db_retry(func, base_delay=0)
        assert result == "ok"
        assert calls == 1

    @pytest.mark.asyncio
    async def test_retries_on_deadlock_then_succeeds(self):
        calls = 0

        async def func():
            nonlocal calls
            calls += 1
            if calls < 2:
                raise _make_dbapi_error("40P01")
            return "recovered"

        result = await with_db_retry(func, base_delay=0)
        assert result == "recovered"
        assert calls == 2

    @pytest.mark.asyncio
    async def test_retries_on_serialization(self):
        calls = 0

        async def func():
            nonlocal calls
            calls += 1
            if calls < 3:
                raise _make_dbapi_error("40001")
            return "ok"

        result = await with_db_retry(func, base_delay=0, max_attempts=3)
        assert calls == 3

    @pytest.mark.asyncio
    async def test_retries_on_lock_not_available(self):
        calls = 0

        async def func():
            nonlocal calls
            calls += 1
            if calls < 2:
                raise _make_dbapi_error("55P03")
            return "ok"

        result = await with_db_retry(func, base_delay=0)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_non_retryable_raises_immediately(self):
        calls = 0

        async def func():
            nonlocal calls
            calls += 1
            raise _make_dbapi_error("23505")

        with pytest.raises(DBAPIError):
            await with_db_retry(func, base_delay=0)
        assert calls == 1

    @pytest.mark.asyncio
    async def test_max_attempts_exhausted_re_raises(self):
        calls = 0

        async def func():
            nonlocal calls
            calls += 1
            raise _make_dbapi_error("40P01")

        with pytest.raises(DBAPIError):
            await with_db_retry(func, base_delay=0, max_attempts=3)
        assert calls == 3

    @pytest.mark.asyncio
    async def test_rollback_called_between_attempts(self):
        calls = {"func": 0, "rollback": 0}

        async def func():
            calls["func"] += 1
            if calls["func"] < 2:
                raise _make_dbapi_error("40P01")
            return "ok"

        async def rollback():
            calls["rollback"] += 1

        await with_db_retry(func, base_delay=0, rollback=rollback)
        assert calls["func"] == 2
        assert calls["rollback"] == 1

    @pytest.mark.asyncio
    async def test_rollback_error_does_not_mask_original(self):
        async def func():
            raise _make_dbapi_error("40P01")

        async def bad_rollback():
            raise RuntimeError("rollback failed")

        with pytest.raises(DBAPIError):
            await with_db_retry(func, base_delay=0, max_attempts=1, rollback=bad_rollback)

    @pytest.mark.asyncio
    async def test_non_dbapi_error_not_retried(self):
        calls = 0

        async def func():
            nonlocal calls
            calls += 1
            raise ValueError("not a db error")

        with pytest.raises(ValueError):
            await with_db_retry(func, base_delay=0)
        assert calls == 1

    @pytest.mark.asyncio
    async def test_delay_uses_jittered_backoff(self):
        sleeps: list[float] = []

        async def func():
            raise _make_dbapi_error("40P01")

        async def fake_sleep(d):
            sleeps.append(d)

        original_sleep = asyncio.sleep
        asyncio.sleep = fake_sleep  # type: ignore[assignment]
        try:
            with pytest.raises(DBAPIError):
                await with_db_retry(func, base_delay=1.0, max_delay=8.0, max_attempts=3)
        finally:
            asyncio.sleep = original_sleep  # type: ignore[assignment]

        assert len(sleeps) == 2
        assert sleeps[0] <= 2.0
        assert sleeps[1] <= 4.0
