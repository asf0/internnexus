"""Unit tests for shared database engine/session factory builders."""

from __future__ import annotations

import pytest
from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine

from internnexus_core.db import (
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


def test_create_sync_engine_with_pooling_strips_asyncpg_driver():
    engine = create_sync_engine_with_pooling(
        "postgresql+asyncpg://user:pass@localhost/db",
    )
    assert isinstance(engine, Engine)
    assert engine.url.drivername == "postgresql"
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
