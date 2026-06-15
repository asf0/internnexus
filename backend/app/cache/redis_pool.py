"""Backward-compatible re-export. Use ``app.cache.cache_service`` instead."""

from app.cache.cache_service import (
    CacheService,
    InMemoryCacheService,
    RedisService,
    _serialize,
    close_redis_pool,
    get_cache_service,
    get_redis,
    get_redis_pool,
    get_redis_service,
)

__all__ = [
    "CacheService",
    "InMemoryCacheService",
    "RedisService",
    "_serialize",
    "close_redis_pool",
    "get_cache_service",
    "get_redis",
    "get_redis_pool",
    "get_redis_service",
]
