"""Unit tests for pipeline/location/cache.py."""

import hashlib
import pytest
from unittest.mock import AsyncMock, patch

from pipeline.location.cache import (
    LocationCache,
    ParsedLocation,
    get_location_cache,
    close_location_cache,
)


class TestParsedLocation:
    """Test suite for ParsedLocation model."""

    def test_parsed_location_creation(self):
        location = ParsedLocation(
            city="San Francisco",
            state="California",
            country="United States",
            is_remote=False,
        )

        assert location.city == "San Francisco"
        assert location.state == "California"
        assert location.country == "United States"
        assert location.is_remote is False

    def test_parsed_location_with_none_values(self):
        location = ParsedLocation(
            city=None,
            state=None,
            country="United States",
            is_remote=True,
        )

        assert location.city is None
        assert location.state is None
        assert location.country == "United States"
        assert location.is_remote is True

    def test_parsed_location_default_is_remote(self):
        location = ParsedLocation(
            city="London",
            state=None,
            country="United Kingdom",
        )

        assert location.is_remote is False

    def test_parsed_location_model_dump_json(self):
        location = ParsedLocation(
            city="Paris",
            state=None,
            country="France",
            is_remote=False,
        )

        json_str = location.model_dump_json()

        assert '"city":"Paris"' in json_str
        assert '"country":"France"' in json_str
        assert '"is_remote":false' in json_str

    def test_parsed_location_model_validate_json(self):
        json_str = '{"city":"Berlin","state":null,"country":"Germany","is_remote":false}'

        location = ParsedLocation.model_validate_json(json_str)

        assert location.city == "Berlin"
        assert location.state is None
        assert location.country == "Germany"
        assert location.is_remote is False

    def test_parsed_location_serialization_roundtrip(self):
        original = ParsedLocation(
            city="Tokyo",
            state=None,
            country="Japan",
            is_remote=False,
        )

        json_str = original.model_dump_json()
        restored = ParsedLocation.model_validate_json(json_str)

        assert restored.city == original.city
        assert restored.state == original.state
        assert restored.country == original.country
        assert restored.is_remote == original.is_remote


class TestLocationCacheKeyGeneration:
    """Test suite for LocationCache key generation."""

    def test_key_generation_consistent(self):
        cache = LocationCache()
        location = "San Francisco, CA"

        key1 = cache._key(location)
        key2 = cache._key(location)

        assert key1 == key2

    def test_key_generation_different_locations(self):
        cache = LocationCache()

        key1 = cache._key("San Francisco, CA")
        key2 = cache._key("New York, NY")

        assert key1 != key2

    def test_key_generation_format(self):
        cache = LocationCache()
        location = "Test Location"

        key = cache._key(location)

        assert key.startswith("location:v1:")
        expected_hash = hashlib.md5(location.encode()).hexdigest()[:16]
        assert key == f"location:v1:{expected_hash}"

    def test_key_generation_with_special_characters(self):
        cache = LocationCache()

        key1 = cache._key("São Paulo, Brazil")
        key2 = cache._key("Köln, Germany")

        assert key1.startswith("location:v1:")
        assert key2.startswith("location:v1:")
        assert key1 != key2

    def test_key_generation_with_empty_string(self):
        cache = LocationCache()

        key = cache._key("")

        assert key.startswith("location:v1:")


class TestLocationCacheWithMockRedis:
    """Test suite for LocationCache with mocked Redis."""

    @pytest.fixture
    def mock_redis(self):
        redis_mock = AsyncMock()
        redis_mock.ping = AsyncMock(return_value=True)
        redis_mock.get = AsyncMock(return_value=None)
        redis_mock.setex = AsyncMock(return_value=True)
        redis_mock.close = AsyncMock(return_value=None)
        return redis_mock

    @pytest.fixture
    def cache(self):
        return LocationCache(redis_url="redis://localhost:6379/0")

    @pytest.mark.asyncio
    async def test_get_returns_none_when_not_connected(self, cache):
        result = await cache.get("San Francisco, CA")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_does_nothing_when_not_connected(self, cache):
        location = ParsedLocation(
            city="San Francisco",
            state="California",
            country="United States",
        )

        await cache.set("San Francisco, CA", location)

    @pytest.mark.asyncio
    async def test_get_returns_cached_value(self, cache, mock_redis):
        cached_json = '{"city":"San Francisco","state":"California","country":"United States","is_remote":false}'
        mock_redis.get = AsyncMock(return_value=cached_json)

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            await cache.connect()
            result = await cache.get("San Francisco, CA")

        assert result is not None
        assert result.city == "San Francisco"
        assert result.state == "California"
        assert result.country == "United States"

    @pytest.mark.asyncio
    async def test_set_stores_value(self, cache, mock_redis):
        location = ParsedLocation(
            city="New York",
            state="New York",
            country="United States",
        )

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            await cache.connect()
            await cache.set("New York, NY", location)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0].startswith("location:v1:")
        assert call_args[0][1] == 86400

    @pytest.mark.asyncio
    async def test_close_disconnects_redis(self, cache, mock_redis):
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            await cache.connect()
            await cache.close()

        mock_redis.close.assert_called_once()
        assert cache._redis is None
        assert cache._connected is False


class TestLocationCacheGracefulDegradation:
    """Test suite for LocationCache graceful degradation when Redis unavailable."""

    @pytest.fixture
    def cache(self):
        return LocationCache(redis_url="redis://invalid:6379/0")

    @pytest.mark.asyncio
    async def test_connect_handles_connection_error(self, cache):
        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(side_effect=Exception("Connection refused"))
            mock_from_url.return_value = mock_redis

            await cache.connect()

        assert cache._connected is False
        assert cache._redis is None

    @pytest.mark.asyncio
    async def test_get_returns_none_on_redis_error(self, cache):
        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(return_value=True)
            mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))
            mock_from_url.return_value = mock_redis

            await cache.connect()
            result = await cache.get("Test Location")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_handles_redis_error_gracefully(self, cache):
        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(return_value=True)
            mock_redis.setex = AsyncMock(side_effect=Exception("Redis error"))
            mock_from_url.return_value = mock_redis

            await cache.connect()
            location = ParsedLocation(city="Test", state=None, country="Test")

            await cache.set("Test Location", location)

    @pytest.mark.asyncio
    async def test_operations_without_connect(self, cache):
        result = await cache.get("Any Location")
        assert result is None

        location = ParsedLocation(city="Test", state=None, country="Test")
        await cache.set("Any Location", location)


class TestGlobalCacheFunctions:
    """Test suite for global cache functions."""

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
