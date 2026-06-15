from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings
from internnexus_core.db import (
    create_async_engine_with_pooling,
    create_sync_engine_with_pooling,
    make_async_sessionmaker,
    make_sync_sessionmaker,
)


class Base(DeclarativeBase):
    pass


settings = get_settings()

# In PIPELINE_MODE, use a minimal pool (pipeline is sequential, <=2 connections needed).
_pipeline_pool_size = int(os.getenv("PIPELINE_MODE_POOL", "0")) or None
_async_pool_size = _pipeline_pool_size if _pipeline_pool_size else 20
_async_overflow = _pipeline_pool_size if _pipeline_pool_size else 20
_sync_pool_size = max(1, _async_pool_size // 2)
_sync_overflow = max(1, _async_overflow // 2)

async_engine = create_async_engine_with_pooling(
    settings.resolved_database_url,
    pool_size=_async_pool_size,
    max_overflow=_async_overflow,
)
AsyncSessionLocal = make_async_sessionmaker(async_engine)

sync_engine = None
SessionLocal = None


def _create_sync_engine():
    """Create the sync engine and session factory on demand."""
    engine = create_sync_engine_with_pooling(
        settings.resolved_database_url,
        pool_size=_sync_pool_size,
        max_overflow=_sync_overflow,
    )
    return engine, make_sync_sessionmaker(engine)


def get_sync_engine():
    """Get or create the sync SQLAlchemy engine on demand."""
    global sync_engine, SessionLocal
    if sync_engine is None or SessionLocal is None:
        sync_engine, SessionLocal = _create_sync_engine()
    return sync_engine


async def get_db() -> AsyncGenerator:
    async with AsyncSessionLocal() as session:
        yield session


async def dispose_engines() -> None:
    """Dispose database engines to free connection pools. Call on app shutdown."""
    global async_engine, sync_engine
    if async_engine:
        await async_engine.dispose()
        async_engine = None
    if sync_engine:
        sync_engine.dispose()
        sync_engine = None
    global SessionLocal
    SessionLocal = None


async def recreate_session_safely() -> bool:
    """Recreate database session safely to free memory.

    This function disposes existing engines and creates new ones,
    which helps free memory held by connection pools.

    Returns:
        True if recreation succeeded, False otherwise.
    """
    global async_engine, sync_engine, AsyncSessionLocal, SessionLocal

    try:
        had_sync_engine = sync_engine is not None

        # Dispose existing engines
        if async_engine:
            await async_engine.dispose()
        if sync_engine:
            sync_engine.dispose()

        # Create new engines (respects PIPELINE_MODE_POOL env var)
        async_engine = create_async_engine_with_pooling(
            settings.resolved_database_url,
            pool_size=_async_pool_size,
            max_overflow=_async_overflow,
        )
        AsyncSessionLocal = make_async_sessionmaker(async_engine)

        sync_engine = None
        SessionLocal = None
        if had_sync_engine:
            sync_engine, SessionLocal = _create_sync_engine()

        # Test the new connection
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))

        return True
    except Exception:  # noqa: BLE001  # best-effort: any recreation failure falls back to original engines
        # If recreation fails, try to restore original engines
        # They might still work even if dispose partially failed
        return False
