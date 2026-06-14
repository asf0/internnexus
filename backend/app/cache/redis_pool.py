"""Cache service with optional Redis or in-memory TTL fallback.

Redis is a soft optional dependency: the ``redis`` package is only imported
when ``REDIS_URL`` is configured. If it is missing from the environment, an
in-memory TTL cache is used instead.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Protocol, runtime_checkable

from app.config import get_settings

logger = logging.getLogger(__name__)

_pool: Any | None = None

# In-memory cache defaults when Redis is not configured.
_DEFAULT_IN_MEMORY_MAXSIZE = 1000


def _import_redis() -> Any:
    """Lazily import redis.asyncio so redis remains an optional dependency."""
    try:
        import redis.asyncio as redis
    except ImportError as exc:
        raise RuntimeError(
            "Redis is configured but the 'redis' package is not installed. "
            "Install it or leave REDIS_URL empty to use the in-memory cache."
        ) from exc
    return redis


async def get_redis_pool() -> Any:
    """Get or create the Redis connection pool."""
    global _pool
    if _pool is None:
        redis = _import_redis()
        settings = get_settings()
        if not settings.redis_url:
            raise RuntimeError("Redis is not configured (REDIS_URL is empty)")
        _pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )
        logger.info("Redis connection pool created")
    return _pool


async def get_redis() -> Any:
    """Get a Redis client from the connection pool."""
    redis = _import_redis()
    pool = await get_redis_pool()
    return redis.Redis(connection_pool=pool)


async def close_redis_pool() -> None:
    """Close the Redis connection pool. Call on app shutdown."""
    global _pool
    if _pool is not None:
        await _pool.disconnect()
        _pool = None
        logger.info("Redis connection pool closed")


def _serialize(value: Any) -> str:
    """Serialize a value to JSON, handling Pydantic and SQLAlchemy ORM models."""
    if hasattr(value, "model_dump"):
        return json.dumps(value.model_dump())
    if hasattr(value, "__dict__") and hasattr(value.__class__, "__tablename__"):
        # SQLAlchemy ORM model - convert to dict
        from sqlalchemy.inspection import inspect as sa_inspect

        mapper = sa_inspect(value.__class__)
        data = {c.key: getattr(value, c.key) for c in mapper.columns}
        return json.dumps(data, default=str)
    return json.dumps(value, default=str)


@runtime_checkable
class CacheService(Protocol):
    """Protocol implemented by both Redis and in-memory cache services."""

    async def get(self, key: str) -> Any | None: ...
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool: ...
    async def delete(self, key: str) -> bool: ...
    async def close(self) -> None: ...


class RedisService:
    """Redis cache service with common operations."""

    def __init__(self, client: Any | None = None):
        self._client = client
        self._owns_client = client is None

    async def _get_client(self) -> Any:
        if self._client is None:
            self._client = await get_redis()
        return self._client

    async def close(self) -> None:
        """Close the client if we own it."""
        if self._owns_client and self._client is not None:
            await self._client.close()
            self._client = None

    async def get(self, key: str) -> Any | None:
        """Get a value from cache."""
        client = await self._get_client()
        redis = _import_redis()
        try:
            value = await client.get(key)
            if value:
                logger.debug(f"[CACHE] hit: {key[:50]}...")
                return json.loads(value)
            logger.debug(f"[CACHE] miss: {key[:50]}...")
            return None
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set a value in cache with TTL."""
        client = await self._get_client()
        redis = _import_redis()
        try:
            serialized = _serialize(value)
            await client.setex(key, ttl, serialized)
            return True
        except redis.RedisError as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        client = await self._get_client()
        redis = _import_redis()
        try:
            await client.delete(key)
            return True
        except redis.RedisError as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False


class InMemoryCacheService:
    """In-memory TTL cache service implementing the same protocol as RedisService."""

    def __init__(self, maxsize: int = _DEFAULT_IN_MEMORY_MAXSIZE):
        self._cache: dict[str, tuple[str, float]] = {}
        self._maxsize = maxsize
        self._lock = asyncio.Lock()

    async def _prune_expired(self) -> None:
        """Remove entries whose TTL has expired."""
        now = time.monotonic()
        expired = [key for key, (_, expiry) in self._cache.items() if expiry <= now]
        for key in expired:
            del self._cache[key]

    async def _enforce_size(self) -> None:
        """Remove oldest entries if the cache exceeds its max size."""
        if len(self._cache) > self._maxsize:
            overflow = len(self._cache) - self._maxsize
            for key in list(self._cache.keys())[:overflow]:
                del self._cache[key]

    async def close(self) -> None:
        """Clear the in-memory cache."""
        async with self._lock:
            self._cache.clear()

    async def get(self, key: str) -> Any | None:
        """Get a value from the in-memory cache."""
        async with self._lock:
            await self._prune_expired()
            entry = self._cache.get(key)
            if entry is None:
                logger.debug(f"[CACHE] miss: {key[:50]}...")
                return None

            value_json, expiry = entry
            if time.monotonic() >= expiry:
                del self._cache[key]
                logger.debug(f"[CACHE] miss: {key[:50]}...")
                return None

            logger.debug(f"[CACHE] hit: {key[:50]}...")
            try:
                return json.loads(value_json)
            except json.JSONDecodeError as e:
                logger.warning(f"Cache get decode error for key {key}: {e}")
                return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set a value in the in-memory cache with per-key TTL."""
        async with self._lock:
            try:
                serialized = _serialize(value)
            except (TypeError, ValueError) as e:
                logger.warning(f"Cache set serialization error for key {key}: {e}")
                return False

            expiry = time.monotonic() + ttl
            self._cache[key] = (serialized, expiry)
            await self._prune_expired()
            await self._enforce_size()
            return True

    async def delete(self, key: str) -> bool:
        """Delete a key from the in-memory cache."""
        async with self._lock:
            self._cache.pop(key, None)
            return True


async def get_redis_service() -> RedisService | InMemoryCacheService:
    """Return a cache service: Redis when configured, otherwise in-memory."""
    settings = get_settings()
    if settings.redis_url:
        return RedisService()
    return InMemoryCacheService()
