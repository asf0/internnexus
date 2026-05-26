"""Unit tests for pipeline/location/cache.py."""

import hashlib
from unittest.mock import AsyncMock, patch

import pytest

from pipeline.location.cache import LocationCache, ParsedLocation, close_location_cache, get_location_cache


class TestParsedLocation:
    def test_roundtrip_json(self):
        original = ParsedLocation(city="Tokyo", state=None, country="Japan", is_remote=False)
        restored = ParsedLocation.model_validate_json(original.model_dump_json())

        assert restored == original

    def test_default_is_remote(self):
        location = ParsedLocation(city="Paris", state=None, country="France")
        assert location.is_remote is False


class TestLocationCacheKeyGeneration:
    def test_key_generation_consistent(self):
        cache = LocationCache()
        location = "San Francisco, CA"

        assert cache._key(location) == cache._key(location)

    def test_key_generation_format(self):
        cache = LocationCache()
        location = "Test Location"
        key = cache._key(location)

        assert key.startswith("location:v1:")
        assert key == f"location:v1:{hashlib.md5(location.encode()).hexdigest()[:16]}"


class TestLocationCacheInMemory:
    @pytest.mark.asyncio
    async def test_get_returns_none_when_missing(self):
        cache = LocationCache()

        assert await cache.get("Missing") is None

    @pytest.mark.asyncio
    async def test_set_and_get_round_trip(self):
        cache = LocationCache()
        location = ParsedLocation(city="New York", state="New York", country="United States")

        await cache.set("New York, NY", location)
        cached = await cache.get("New York, NY")

        assert cached == location

    @pytest.mark.asyncio
    async def test_expired_entries_are_evicted(self, monkeypatch):
        cache = LocationCache()
        location = ParsedLocation(city="Berlin", state=None, country="Germany")
        current_time = 100.0

        monkeypatch.setattr("pipeline.location.cache.time.monotonic", lambda: current_time)
        await cache.set("Berlin", location)

        current_time += cache.TTL_SECONDS + 1
        assert await cache.get("Berlin") is None

    @pytest.mark.asyncio
    async def test_close_clears_entries(self):
        cache = LocationCache()
        location = ParsedLocation(city="London", state=None, country="United Kingdom")

        await cache.set("London", location)
        await cache.close()

        assert await cache.get("London") is None


class TestGlobalCacheFunctions:
    def setup_method(self):
        import pipeline.location.cache as cache_module

        cache_module._location_cache = None

    @pytest.mark.asyncio
    async def test_get_location_cache_creates_singleton(self):
        with patch.object(LocationCache, "connect", new_callable=AsyncMock):
            cache1 = await get_location_cache()
            cache2 = await get_location_cache()

        assert cache1 is cache2

    @pytest.mark.asyncio
    async def test_close_location_cache_resets_singleton(self):
        with patch.object(LocationCache, "connect", new_callable=AsyncMock):
            cache = await get_location_cache()
            assert cache is not None

        with patch.object(LocationCache, "close", new_callable=AsyncMock):
            await close_location_cache()

        import pipeline.location.cache as cache_module

        assert cache_module._location_cache is None

    @pytest.mark.asyncio
    async def test_close_location_cache_when_none(self):
        import pipeline.location.cache as cache_module

        cache_module._location_cache = None
        await close_location_cache()
