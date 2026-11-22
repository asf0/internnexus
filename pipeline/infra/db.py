from __future__ import annotations

from typing import TYPE_CHECKING

from internnexus_core.db import DatabaseRuntime
from pipeline.infra.settings import get_settings

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
    from sqlalchemy.orm import Session, sessionmaker

    async_engine: AsyncEngine
    sync_engine: Engine | None
    AsyncSessionLocal: async_sessionmaker[AsyncSession]
    SessionLocal: sessionmaker[Session]

__all__ = ["dispose_engines"]


settings = get_settings()

_runtime = DatabaseRuntime(
    settings.resolved_database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
)

# Engines and session factories (async_engine, AsyncSessionLocal, ...) resolve
# through the runtime so recreate/dispose rebinds stay visible at module level.
__getattr__ = _runtime.module_getattr(__name__)
dispose_engines = _runtime.dispose_engines
