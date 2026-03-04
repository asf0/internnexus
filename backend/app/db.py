from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

# In PIPELINE_MODE, use a minimal pool (pipeline is sequential, ≤2 connections needed).
_pipeline_pool_size = int(os.getenv("PIPELINE_MODE_POOL", "0")) or None
_async_pool_size = _pipeline_pool_size if _pipeline_pool_size else 20
_async_overflow = _pipeline_pool_size if _pipeline_pool_size else 20
_sync_pool_size = max(1, _async_pool_size // 2)
_sync_overflow = max(1, _async_overflow // 2)

async_engine = create_async_engine(
    settings.resolved_database_url,
    pool_pre_ping=True,
    pool_size=_async_pool_size,
    max_overflow=_async_overflow,
    pool_timeout=30,
    pool_recycle=900,
)
AsyncSessionLocal = async_sessionmaker(bind=async_engine, autoflush=False, autocommit=False)

sync_engine = create_engine(
    settings.resolved_database_url.replace("+asyncpg", ""),
    pool_pre_ping=True,
    pool_size=_sync_pool_size,
    max_overflow=_sync_overflow,
    pool_timeout=30,
    pool_recycle=900,
)
SessionLocal = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False)


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


async def recreate_session_safely() -> bool:
    """Recreate database session safely to free memory.

    This function disposes existing engines and creates new ones,
    which helps free memory held by connection pools.

    Returns:
        True if recreation succeeded, False otherwise.
    """
    global async_engine, sync_engine, AsyncSessionLocal, SessionLocal

    try:
        # Dispose existing engines
        if async_engine:
            await async_engine.dispose()
        if sync_engine:
            sync_engine.dispose()

        # Create new engines (respects PIPELINE_MODE_POOL env var)
        async_engine = create_async_engine(
            settings.resolved_database_url,
            pool_pre_ping=True,
            pool_size=_async_pool_size,
            max_overflow=_async_overflow,
            pool_timeout=30,
            pool_recycle=900,
        )
        AsyncSessionLocal = async_sessionmaker(bind=async_engine, autoflush=False, autocommit=False)

        sync_engine = create_engine(
            settings.resolved_database_url.replace("+asyncpg", ""),
            pool_pre_ping=True,
            pool_size=_sync_pool_size,
            max_overflow=_sync_overflow,
            pool_timeout=30,
            pool_recycle=900,
        )
        SessionLocal = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False)

        # Test the new connection
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))

        return True
    except Exception:
        # If recreation fails, try to restore original engines
        # They might still work even if dispose partially failed
        return False
