"""Redis-backed cache for location parsing results."""

from __future__ import annotations

import hashlib
import logging
import os

import redis.asyncio as redis
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ParsedLocation(BaseModel):
    city: str | None
    state: str | None
    country: str | None
    is_remote: bool = False


class LocationCache:
    CACHE_PREFIX = "location:v1:"
    TTL_SECONDS = 86400

    def __init__(self, redis_url: str | None = None):
        self._redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._redis: redis.Redis | None = None
        self._connected = False

    async def connect(self) -> None:
        if self._redis is None:
            try:
                self._redis = redis.from_url(self._redis_url, decode_responses=True)
                await self._redis.ping()
                self._connected = True
                logger.debug("LocationCache connected to Redis")
            except redis.RedisError as e:
                logger.warning(f"LocationCache failed to connect to Redis: {e}")
                self._redis = None
                self._connected = False

    async def close(self) -> None:
        if self._redis:
            try:
                await self._redis.close()
            except redis.RedisError:
                pass
            self._redis = None
            self._connected = False

    def _key(self, location: str) -> str:
        hash_val = hashlib.md5(location.encode()).hexdigest()[:16]
        return f"{self.CACHE_PREFIX}{hash_val}"

    async def get(self, location: str) -> ParsedLocation | None:
        if not self._redis or not self._connected:
            return None
        try:
            key = self._key(location)
            data = await self._redis.get(key)
            if data:
                return ParsedLocation.model_validate_json(data)
        except redis.RedisError as e:
            logger.debug(f"LocationCache get error: {e}")
        return None

    async def set(self, location: str, result: ParsedLocation) -> None:
        if not self._redis or not self._connected:
            return
        try:
            key = self._key(location)
            await self._redis.setex(key, self.TTL_SECONDS, result.model_dump_json())
        except redis.RedisError as e:
            logger.debug(f"LocationCache set error: {e}")


_location_cache: LocationCache | None = None


async def get_location_cache() -> LocationCache:
    global _location_cache
    if _location_cache is None:
        _location_cache = LocationCache()
        await _location_cache.connect()
    return _location_cache


async def close_location_cache() -> None:
    global _location_cache
    if _location_cache is not None:
        await _location_cache.close()
        _location_cache = None
