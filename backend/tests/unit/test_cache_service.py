"""Tests for the cache service: in-memory fallback and cache factory."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from app.cache.cache_service import (
    CacheService,
    InMemoryCacheService,
    close_cache_service,
    get_cache_service,
)


class TestInMemoryCacheService:
    """Tests for InMemoryCacheService protocol compliance."""

    @pytest.fixture
    def cache(self) -> InMemoryCacheService:
        return InMemoryCacheService(maxsize=10)

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing_key(self, cache: InMemoryCacheService) -> None:
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get_roundtrip(self, cache: InMemoryCacheService) -> None:
        await cache.set("key1", {"value": 42}, ttl=60)
        result = await cache.get("key1")
        assert result == {"value": 42}

    @pytest.mark.asyncio
    async def test_expired_entry_returns_none(self, cache: InMemoryCacheService) -> None:
        await cache.set("key1", "data", ttl=0)
        await asyncio.sleep(0.01)
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_removes_entry(self, cache: InMemoryCacheService) -> None:
        await cache.set("key1", "data", ttl=60)
        deleted = await cache.delete("key1")
        assert deleted is True
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_delete_missing_key_returns_true(self, cache: InMemoryCacheService) -> None:
        deleted = await cache.delete("nonexistent")
        assert deleted is True

    @pytest.mark.asyncio
    async def test_maxsize_eviction(self, cache: InMemoryCacheService) -> None:
        for i in range(15):
            await cache.set(f"key{i}", i, ttl=60)
        assert len(cache._cache) <= 10

    @pytest.mark.asyncio
    async def test_close_clears_cache(self, cache: InMemoryCacheService) -> None:
        await cache.set("key1", "data", ttl=60)
        await cache.close()
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_set_serializes_pydantic_models(self, cache: InMemoryCacheService) -> None:
        class FakeModel:
            def model_dump(self, mode: str = "python") -> dict:
                return {"id": 1, "name": "test"}

        await cache.set("model_key", FakeModel(), ttl=60)
        result = await cache.get("model_key")
        assert result == {"id": 1, "name": "test"}

    @pytest.mark.asyncio
    async def test_protocol_compliance(self, cache: InMemoryCacheService) -> None:
        assert isinstance(cache, CacheService)


class TestCacheFactory:
    """Tests for get_cache_service factory behavior."""

    @pytest.fixture(autouse=True)
    async def _reset_process_cache(self) -> None:
        await close_cache_service()
        yield
        await close_cache_service()

    @pytest.mark.asyncio
    async def test_returns_in_memory_when_redis_url_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "app.cache.cache_service.get_settings",
            lambda: SimpleNamespace(redis_url=""),
        )
        service = await get_cache_service()
        assert isinstance(service, InMemoryCacheService)

    @pytest.mark.asyncio
    async def test_in_memory_service_is_shared_across_factory_calls(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "app.cache.cache_service.get_settings",
            lambda: SimpleNamespace(redis_url=""),
        )

        first = await get_cache_service()
        second = await get_cache_service()

        assert first is second
        await first.set("shared:key", {"value": 42}, ttl=60)
        assert await second.get("shared:key") == {"value": 42}
