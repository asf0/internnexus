"""Shared database engine and session factory builders.

These are pure functions that accept explicit connection parameters.  They do
not read service-specific settings or manage global state.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

DEFAULT_POOL_TIMEOUT = 30
DEFAULT_POOL_RECYCLE = 900


def create_async_engine_with_pooling(
    database_url: str,
    *,
    pool_size: int | None = None,
    max_overflow: int | None = None,
    pool_timeout: int = DEFAULT_POOL_TIMEOUT,
    pool_recycle: int = DEFAULT_POOL_RECYCLE,
    pool_pre_ping: bool = True,
) -> AsyncEngine:
    """Create an async SQLAlchemy engine with connection-pooling defaults."""
    return create_async_engine(
        database_url,
        pool_pre_ping=pool_pre_ping,
        pool_size=pool_size if pool_size is not None else 20,
        max_overflow=max_overflow if max_overflow is not None else 20,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
    )


def create_sync_engine_with_pooling(
    database_url: str,
    *,
    pool_size: int | None = None,
    max_overflow: int | None = None,
    pool_timeout: int = DEFAULT_POOL_TIMEOUT,
    pool_recycle: int = DEFAULT_POOL_RECYCLE,
    pool_pre_ping: bool = True,
) -> Engine:
    """Create a sync SQLAlchemy engine with connection-pooling defaults.

    The asyncpg driver prefix is stripped automatically so callers can pass the
    same async URL used for the async engine.
    """
    sync_url = database_url.replace("+asyncpg", "")
    return create_engine(
        sync_url,
        pool_pre_ping=pool_pre_ping,
        pool_size=pool_size if pool_size is not None else 10,
        max_overflow=max_overflow if max_overflow is not None else 10,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
    )


def make_async_sessionmaker(engine: AsyncEngine) -> async_sessionmaker:
    """Create an async session factory bound to *engine*."""
    return async_sessionmaker(bind=engine, autoflush=False, autocommit=False)


def make_sync_sessionmaker(engine: Engine) -> sessionmaker:
    """Create a sync session factory bound to *engine*."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
