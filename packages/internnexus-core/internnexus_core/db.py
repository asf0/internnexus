"""Shared database engine and session factory builders.

These are pure functions that accept explicit connection parameters.  They do
not read service-specific settings or manage global state.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator, Callable

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

DEFAULT_POOL_TIMEOUT = 30
DEFAULT_POOL_RECYCLE = 900

_RUNTIME_ATTRS = {"async_engine", "sync_engine"}
_SESSION_FACTORY_ATTRS = {
    "AsyncSessionLocal": "async_session_local",
    "SessionLocal": "session_local",
}


def create_async_engine_with_pooling(
    database_url: str,
    *,
    pool_size: int | None = None,
    max_overflow: int | None = None,
    pool_timeout: int = DEFAULT_POOL_TIMEOUT,
    pool_recycle: int = DEFAULT_POOL_RECYCLE,
    pool_pre_ping: bool = True,
    statement_cache_size: int | None = None,
) -> AsyncEngine:
    """Create an async SQLAlchemy engine with connection-pooling defaults.

    ``statement_cache_size`` is passed through to asyncpg via ``connect_args``.
    It must be set to 0 when connecting through PgBouncer in transaction
    pooling mode, since asyncpg's named prepared statements don't survive
    connections being handed off between clients. Left unset (None), no
    ``connect_args`` are passed and behavior is unchanged.
    """
    engine_kwargs: dict = {
        "pool_pre_ping": pool_pre_ping,
        "pool_size": pool_size if pool_size is not None else 20,
        "max_overflow": max_overflow if max_overflow is not None else 20,
        "pool_timeout": pool_timeout,
        "pool_recycle": pool_recycle,
    }
    if statement_cache_size is not None:
        engine_kwargs["connect_args"] = {
            **engine_kwargs.get("connect_args", {}),
            "statement_cache_size": statement_cache_size,
        }
    return create_async_engine(database_url, **engine_kwargs)


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

    The asyncpg driver prefix is replaced with psycopg2 so callers can pass the
    same async URL used for the async engine. The driver is named explicitly
    because SQLAlchemy 2.1 changed the default DBAPI for bare ``postgresql://``
    URLs from psycopg2 to psycopg v3.
    """
    sync_url = database_url.replace("+asyncpg", "+psycopg2")
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


class DatabaseRuntime:
    """Engine and session-factory lifecycle for one service process.

    Owns the async engine (created eagerly), an on-demand sync engine, and
    the recreate/dispose behavior both backend and pipeline previously
    duplicated. Callers expose the attributes they need at module level.
    """

    def __init__(
        self,
        database_url: str,
        *,
        pool_size: int,
        max_overflow: int,
        statement_cache_size: int | None = None,
    ) -> None:
        self._database_url = database_url
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._sync_pool_size = max(1, pool_size // 2)
        self._sync_overflow = max(1, max_overflow // 2)
        self._statement_cache_size = statement_cache_size
        self._logger = logging.getLogger(__name__)

        self.async_engine: AsyncEngine | None = create_async_engine_with_pooling(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            statement_cache_size=statement_cache_size,
        )
        self.async_session_local: async_sessionmaker = make_async_sessionmaker(self.async_engine)
        self.sync_engine: Engine | None = None
        self.session_local: sessionmaker | None = None

    def _create_sync_engine(self) -> tuple[Engine, sessionmaker]:
        engine = create_sync_engine_with_pooling(
            self._database_url,
            pool_size=self._sync_pool_size,
            max_overflow=self._sync_overflow,
        )
        return engine, make_sync_sessionmaker(engine)

    def get_sync_engine(self) -> Engine:
        """Get or create the sync SQLAlchemy engine on demand."""
        if self.sync_engine is None or self.session_local is None:
            self.sync_engine, self.session_local = self._create_sync_engine()
        return self.sync_engine

    async def get_db(self) -> AsyncGenerator:
        """Yield a request-scoped async session (FastAPI dependency shape)."""
        async with self.async_session_local() as session:
            yield session

    def module_getattr(self, module_name: str) -> Callable[[str], object]:
        """Build a module-level ``__getattr__`` exposing this runtime's state.

        Engines and session factories live on the runtime so that
        recreate/dispose rebinds stay visible through module attribute access.
        """

        def _module_getattr(name: str) -> object:
            if name in _RUNTIME_ATTRS:
                return getattr(self, name)
            if name in _SESSION_FACTORY_ATTRS:
                return getattr(self, _SESSION_FACTORY_ATTRS[name])
            raise AttributeError(f"module {module_name!r} has no attribute {name!r}")

        return _module_getattr

    async def dispose_engines(self) -> None:
        """Dispose database engines to free connection pools. Call on shutdown."""
        if self.async_engine:
            await self.async_engine.dispose()
            self.async_engine = None
        if self.sync_engine:
            self.sync_engine.dispose()
            self.sync_engine = None
        self.session_local = None

    async def recreate_session_safely(self) -> bool:
        """Recreate engines and session factories to free pool memory.

        Returns True if recreation succeeded, False otherwise (the original
        engines are kept as a best effort).
        """
        try:
            had_sync_engine = self.sync_engine is not None

            if self.async_engine:
                await self.async_engine.dispose()
            if self.sync_engine:
                self.sync_engine.dispose()

            self.async_engine = create_async_engine_with_pooling(
                self._database_url,
                pool_size=self._pool_size,
                max_overflow=self._max_overflow,
                statement_cache_size=self._statement_cache_size,
            )
            self.async_session_local = make_async_sessionmaker(self.async_engine)

            self.sync_engine = None
            self.session_local = None
            if had_sync_engine:
                self.sync_engine, self.session_local = self._create_sync_engine()

            async with self.async_session_local() as session:
                await session.execute(text("SELECT 1"))

            return True
        except Exception:  # noqa: BLE001  # best-effort: any recreation failure falls back to original engines
            self._logger.warning("Engine recreation failed; keeping existing engines", exc_info=True)
            return False
