from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from pipeline.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

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

sync_engine = None
SessionLocal = None


def _create_sync_engine():
    engine = create_engine(
        settings.resolved_database_url.replace("+asyncpg", ""),
        pool_pre_ping=True,
        pool_size=_sync_pool_size,
        max_overflow=_sync_overflow,
        pool_timeout=30,
        pool_recycle=900,
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return engine, session_factory


def get_sync_engine():
    global sync_engine, SessionLocal
    if sync_engine is None or SessionLocal is None:
        sync_engine, SessionLocal = _create_sync_engine()
    return sync_engine


async def get_db() -> AsyncGenerator:
    async with AsyncSessionLocal() as session:
        yield session


async def dispose_engines() -> None:
    global async_engine, sync_engine, SessionLocal
    if async_engine:
        await async_engine.dispose()
        async_engine = None
    if sync_engine:
        sync_engine.dispose()
        sync_engine = None
    SessionLocal = None


async def recreate_session_safely() -> bool:
    global async_engine, sync_engine, AsyncSessionLocal, SessionLocal
    try:
        had_sync_engine = sync_engine is not None
        if async_engine:
            await async_engine.dispose()
        if sync_engine:
            sync_engine.dispose()
        async_engine = create_async_engine(
            settings.resolved_database_url,
            pool_pre_ping=True,
            pool_size=_async_pool_size,
            max_overflow=_async_overflow,
            pool_timeout=30,
            pool_recycle=900,
        )
        AsyncSessionLocal = async_sessionmaker(bind=async_engine, autoflush=False, autocommit=False)
        sync_engine = None
        SessionLocal = None
        if had_sync_engine:
            sync_engine, SessionLocal = _create_sync_engine()
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
