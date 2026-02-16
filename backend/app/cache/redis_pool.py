"""Redis connection pool and cache service."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import redis.asyncio as redis

from app.config import get_settings

logger = logging.getLogger(__name__)

_pool: redis.ConnectionPool | None = None


async def get_redis_pool() -> redis.ConnectionPool:
    """Get or create the Redis connection pool."""
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )
        logger.info("Redis connection pool created")
    return _pool


async def get_redis() -> redis.Redis:
    """Get a Redis client from the connection pool."""
    pool = await get_redis_pool()
    return redis.Redis(connection_pool=pool)


async def close_redis_pool() -> None:
    """Close the Redis connection pool. Call on app shutdown."""
    global _pool
    if _pool is not None:
        await _pool.disconnect()
        _pool = None
        logger.info("Redis connection pool closed")


class RedisService:
    """Redis cache service with common operations."""

    def __init__(self, client: redis.Redis | None = None):
        self._client = client
        self._owns_client = client is None

    async def _get_client(self) -> redis.Redis:
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
        try:
            # Handle Pydantic models and ORM models
            if hasattr(value, "model_dump"):
                serialized = json.dumps(value.model_dump())
            elif hasattr(value, "__dict__") and hasattr(value.__class__, "__tablename__"):
                # SQLAlchemy ORM model - convert to dict
                from sqlalchemy.inspection import inspect as sa_inspect

                mapper = sa_inspect(value.__class__)
                data = {c.key: getattr(value, c.key) for c in mapper.columns}
                serialized = json.dumps(data, default=str)
            else:
                serialized = json.dumps(value, default=str)
            await client.setex(key, ttl, serialized)
            return True
        except redis.RedisError as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        client = await self._get_client()
        try:
            await client.delete(key)
            return True
        except redis.RedisError as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False

    async def get_embedding(self, text: str) -> list[float] | None:
        """Get cached embedding for text."""
        key = self._embedding_key(text)
        return await self.get(key)

    async def set_embedding(self, text: str, embedding: list[float], ttl: int = 86400) -> bool:
        """Cache an embedding for text."""
        key = self._embedding_key(text)
        return await self.set(key, embedding, ttl)

    @staticmethod
    def _embedding_key(text: str) -> str:
        """Generate cache key for embedding."""
        return f"embed:{hashlib.md5(text.encode()).hexdigest()}"


async def get_redis_service() -> RedisService:
    """Dependency to get a RedisService instance."""
    return RedisService()
