"""Match cache service for storing and retrieving job match results."""

from __future__ import annotations

import logging
from typing import Any

from app.api.schemas import MatchResult
from app.cache.redis_pool import RedisService, get_redis_service

logger = logging.getLogger(__name__)


class MatchCacheService:
    """Service for caching job match results in Redis.

    Provides methods to store, retrieve, and manage paginated match results
    with configurable TTL. Handles serialization of Pydantic models and
    graceful error handling for Redis operations.
    """

    def __init__(self, redis_service: RedisService | None = None):
        """Initialize the match cache service.

        Args:
            redis_service: Optional RedisService instance. If not provided,
                a new instance will be created on first use.
        """
        self._redis = redis_service

    async def _get_redis(self) -> RedisService:
        """Get or create the Redis service instance."""
        if self._redis is None:
            self._redis = await get_redis_service()
        return self._redis

    def _make_key(self, session_id: str) -> str:
        """Generate the Redis key for a session's matches."""
        return f"match:{session_id}"

    async def cache_matches(
        self,
        session_id: str,
        matches: list[MatchResult],
        ttl: int = 1800,
    ) -> bool:
        """Store match results in Redis as a JSON list.

        Args:
            session_id: Unique identifier for the matching session.
            matches: List of MatchResult objects to cache.
            ttl: Time-to-live in seconds (default: 1800 = 30 minutes).

        Returns:
            True if caching succeeded, False otherwise.
        """
        if not matches:
            logger.debug(f"No matches to cache for session {session_id}")
            return True

        redis = await self._get_redis()
        key = self._make_key(session_id)

        try:
            # Convert Pydantic models to dicts for serialization
            matches_data = [match.model_dump(mode="json") for match in matches]

            # Store in Redis with TTL using the public API
            result = await redis.set(key, matches_data, ttl=ttl)
            if result:
                logger.debug(
                    f"Cached {len(matches)} matches for session {session_id} (TTL: {ttl}s)"
                )
            return result
        except Exception as e:
            logger.warning(f"Failed to cache matches for session {session_id}: {e}")
            return False

    async def get_paginated_matches(
        self,
        session_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int] | None:
        """Retrieve paginated matches from Redis.

        Args:
            session_id: Unique identifier for the matching session.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            A tuple of (paginated_items, total_count) if found, None otherwise.
            Returns empty list if page is beyond available data.
        """
        redis = await self._get_redis()
        key = self._make_key(session_id)

        try:
            data = await redis.get(key)
            if data is None:
                logger.debug(f"No cached matches found for session {session_id}")
                return None

            # Data should be a list of dicts
            if not isinstance(data, list):
                logger.warning(f"Invalid cache data format for session {session_id}")
                return None

            matches: list[dict[str, Any]] = data
            total_count = len(matches)

            # Handle pagination
            if page < 1:
                page = 1
            if page_size < 1:
                page_size = 20

            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size

            # Return empty list if page is beyond data
            if start_idx >= total_count:
                return ([], total_count)

            paginated = matches[start_idx:end_idx]
            logger.debug(
                f"Retrieved page {page} ({len(paginated)} items) "
                f"from {total_count} total matches for session {session_id}"
            )
            return (paginated, total_count)

        except Exception as e:
            logger.warning(f"Failed to retrieve matches for session {session_id}: {e}")
            return None

    async def get_total_count(self, session_id: str) -> int | None:
        """Get the total number of cached matches for a session.

        Args:
            session_id: Unique identifier for the matching session.

        Returns:
            Total count of matches if found, None otherwise.
        """
        redis = await self._get_redis()
        key = self._make_key(session_id)

        try:
            data = await redis.get(key)
            if data is None:
                return None

            if not isinstance(data, list):
                logger.warning(f"Invalid cache data format for session {session_id}")
                return None

            return len(data)

        except Exception as e:
            logger.warning(f"Failed to get match count for session {session_id}: {e}")
            return None

    async def delete_matches(self, session_id: str) -> bool:
        """Delete cached matches for a session.

        Args:
            session_id: Unique identifier for the matching session.

        Returns:
            True if deletion succeeded or key didn't exist,
            False if an error occurred.
        """
        redis = await self._get_redis()
        key = self._make_key(session_id)

        try:
            result = await redis.delete(key)
            if result:
                logger.debug(f"Deleted cached matches for session {session_id}")
            else:
                logger.debug(f"No cached matches to delete for session {session_id}")
            return result
        except Exception as e:
            logger.warning(f"Failed to delete matches for session {session_id}: {e}")
            return False


async def get_match_cache_service() -> MatchCacheService:
    """Dependency function to get MatchCacheService instance for FastAPI."""
    return MatchCacheService()
