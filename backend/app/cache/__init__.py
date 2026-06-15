"""Cache module with optional Redis or in-memory TTL fallback."""

from app.cache.cache_service import (
    CacheService,
    InMemoryCacheService,
    RedisService,
    close_cache_service,
    get_cache_service,
    get_redis,
    get_redis_service,
)

__all__ = [
    "CacheService",
    "InMemoryCacheService",
    "RedisService",
    "close_cache_service",
    "get_cache_service",
    "get_redis",
    "get_redis_service",
]
