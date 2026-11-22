"""Unit tests for shared database engine/session factory builders."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine

import internnexus_core.db as db_module
from internnexus_core.db import (
    DatabaseRuntime,
    create_async_engine_with_pooling,
    create_sync_engine_with_pooling,
    make_async_sessionmaker,
    make_sync_sessionmaker,
)


def test_create_async_engine_with_pooling_returns_async_engine():
    engine = create_async_engine_with_pooling(
        "postgresql+asyncpg://user:pass@localhost/db",
    )
    assert isinstance(engine, AsyncEngine)
    assert engine.url.drivername == "postgresql+asyncpg"
    assert engine.url.username == "user"
    assert engine.url.host == "localhost"
    assert engine.url.database == "db"


def test_create_async_engine_with_pooling_uses_custom_sizes():
    engine = create_async_engine_with_pooling(
        "postgresql+asyncpg://user:pass@localhost/db",
        pool_size=5,
        max_overflow=10,
    )
    assert engine.pool.size() == 5
    assert engine.pool._max_overflow == 10


def test_create_sync_engine_with_pooling_uses_psycopg2_driver():
    engine = create_sync_engine_with_pooling(
        "postgresql+asyncpg://user:pass@localhost/db",
    )
    assert isinstance(engine, Engine)
    assert engine.url.drivername == "postgresql+psycopg2"
    assert engine.url.username == "user"
    assert engine.url.host == "localhost"
    assert engine.url.database == "db"


def test_create_sync_engine_with_pooling_uses_custom_sizes():
    engine = create_sync_engine_with_pooling(
        "postgresql+asyncpg://user:pass@localhost/db",
        pool_size=3,
        max_overflow=7,
    )
    assert engine.pool.size() == 3
    assert engine.pool._max_overflow == 7


@pytest.mark.asyncio
async def test_make_async_sessionmaker_is_bound_to_engine():
    engine = create_async_engine_with_pooling(
        "postgresql+asyncpg://user:pass@localhost/db",
    )
    session_maker = make_async_sessionmaker(engine)
    assert session_maker.kw["bind"] is engine


def test_make_sync_sessionmaker_is_bound_to_engine():
    engine = create_sync_engine_with_pooling(
        "postgresql+asyncpg://user:pass@localhost/db",
    )
    session_maker = make_sync_sessionmaker(engine)
    assert session_maker.kw["bind"] is engine


def test_create_async_engine_with_pooling_omits_connect_args_by_default(monkeypatch):
    captured_kwargs: dict = {}

    def fake_create_async_engine(url, **kwargs):
        captured_kwargs.update(kwargs)
        return MagicMock(spec=AsyncEngine)

    monkeypatch.setattr(db_module, "create_async_engine", fake_create_async_engine)

    create_async_engine_with_pooling("postgresql+asyncpg://user:pass@localhost/db")

    assert "connect_args" not in captured_kwargs


def test_create_async_engine_with_pooling_passes_statement_cache_size(monkeypatch):
    captured_kwargs: dict = {}

    def fake_create_async_engine(url, **kwargs):
        captured_kwargs.update(kwargs)
        return MagicMock(spec=AsyncEngine)

    monkeypatch.setattr(db_module, "create_async_engine", fake_create_async_engine)

    create_async_engine_with_pooling(
        "postgresql+asyncpg://user:pass@localhost/db",
        statement_cache_size=0,
    )

    assert captured_kwargs["connect_args"] == {"statement_cache_size": 0}


def test_database_runtime_threads_statement_cache_size_to_async_engine_only(monkeypatch):
    async_calls: list[dict] = []
    sync_calls: list[dict] = []

    def fake_create_async_engine(url, **kwargs):
        async_calls.append(kwargs)
        return MagicMock(spec=AsyncEngine)

    def fake_create_engine(url, **kwargs):
        sync_calls.append(kwargs)
        return MagicMock(spec=Engine)

    monkeypatch.setattr(db_module, "create_async_engine", fake_create_async_engine)
    monkeypatch.setattr(db_module, "create_engine", fake_create_engine)

    runtime = DatabaseRuntime(
        "postgresql+asyncpg://user:pass@localhost/db",
        pool_size=5,
        max_overflow=5,
        statement_cache_size=0,
    )

    assert len(async_calls) == 1
    assert async_calls[0]["connect_args"] == {"statement_cache_size": 0}

    runtime.get_sync_engine()

    assert len(sync_calls) == 1
    assert "connect_args" not in sync_calls[0]
    assert "statement_cache_size" not in sync_calls[0]


@pytest.mark.asyncio
async def test_recreate_session_safely_reapplies_statement_cache_size(monkeypatch):
    async_calls: list[dict] = []

    def fake_create_async_engine(url, **kwargs):
        engine = MagicMock(spec=AsyncEngine)

        async def fake_dispose():
            return None

        engine.dispose = fake_dispose

        session_cm = MagicMock()

        async def fake_execute(*args, **kwargs):
            return None

        session = MagicMock()
        session.execute = fake_execute

        async def aenter(*args, **kwargs):
            return session

        async def aexit(*args, **kwargs):
            return None

        session_cm.__aenter__ = aenter
        session_cm.__aexit__ = aexit
        engine.connect = MagicMock(return_value=session_cm)

        async_calls.append(kwargs)
        return engine

    monkeypatch.setattr(db_module, "create_async_engine", fake_create_async_engine)

    runtime = DatabaseRuntime(
        "postgresql+asyncpg://user:pass@localhost/db",
        pool_size=5,
        max_overflow=5,
        statement_cache_size=0,
    )
    assert len(async_calls) == 1
    assert async_calls[0]["connect_args"] == {"statement_cache_size": 0}

    # Patch the session factory so recreate_session_safely's health check
    # doesn't need a real database connection.
    session = MagicMock()

    async def fake_execute(*args, **kwargs):
        return None

    session.execute = fake_execute

    class FakeSessionCM:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *args):
            return None

    monkeypatch.setattr(db_module, "make_async_sessionmaker", lambda engine: (lambda: FakeSessionCM()))

    result = await runtime.recreate_session_safely()

    assert result is True
    assert len(async_calls) == 2
    assert async_calls[1]["connect_args"] == {"statement_cache_size": 0}
