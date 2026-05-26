"""In-memory cache for location parsing results."""

from __future__ import annotations

import hashlib
import logging
import time

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

    def __init__(self):
        self._entries: dict[str, tuple[float, ParsedLocation]] = {}

    async def connect(self) -> None:
        logger.debug("LocationCache initialized")

    async def close(self) -> None:
        self._entries.clear()

    def _key(self, location: str) -> str:
        hash_val = hashlib.md5(location.encode()).hexdigest()[:16]
        return f"{self.CACHE_PREFIX}{hash_val}"

    async def get(self, location: str) -> ParsedLocation | None:
        key = self._key(location)
        entry = self._entries.get(key)
        if entry is None:
            return None

        expires_at, result = entry
        if expires_at <= time.monotonic():
            self._entries.pop(key, None)
            return None
        return result

    async def set(self, location: str, result: ParsedLocation) -> None:
        key = self._key(location)
        expires_at = time.monotonic() + self.TTL_SECONDS
        self._entries[key] = (expires_at, result)


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
