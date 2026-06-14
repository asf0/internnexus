"""Cache module with optional Redis or in-memory TTL fallback."""

from app.cache.redis_pool import (
    CacheService,
    InMemoryCacheService,
    RedisService,
    get_redis,
    get_redis_service,
)

__all__ = [
    "CacheService",
    "InMemoryCacheService",
    "RedisService",
    "get_redis",
    "get_redis_service",
]
