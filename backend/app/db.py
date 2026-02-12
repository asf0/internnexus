from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

# Async engine and session
async_engine = create_async_engine(settings.resolved_database_url, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(bind=async_engine, autoflush=False, autocommit=False)

# Sync engine and session for ingestion scripts
sync_engine = create_engine(
    settings.resolved_database_url.replace("+asyncpg", ""), pool_pre_ping=True
)
SessionLocal = sessionmaker(bind=sync_engine, autoflush=False, autocommit=False)


async def get_db() -> AsyncGenerator:
    async with AsyncSessionLocal() as session:
        yield session
