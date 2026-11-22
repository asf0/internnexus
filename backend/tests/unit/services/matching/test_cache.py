from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.matching import MatchResult
from app.infra.cache.cache_service import close_cache_service
from app.services.matching.cache import MatchCacheService


class FakeRedisService:
    def __init__(self):
        self._store: dict[str, object] = {}

    async def set(self, key: str, value, ttl: int = 3600):  # noqa: ANN001
        self._store[key] = value
        return True

    async def get(self, key: str):
        return self._store.get(key)

    async def delete(self, key: str):
        return self._store.pop(key, None) is not None


def _match(job_suffix: str) -> MatchResult:
    return MatchResult(
        job_id=uuid4(),
        score=0.8,
        match_percentage=80.0,
        title=f"Job {job_suffix}",
        company="TestCo",
        location="Remote",
        apply_url="https://example.com/apply",
        description_html="<p>Python backend role</p>",
        posted_at=datetime.now(timezone.utc),
        score_breakdown={
            "semantic": 0.8,
            "skill_title": 0.8,
            "work_mode": 0.6,
            "recency": 0.9,
            "final": 0.8,
        },
    )


@pytest.mark.asyncio
async def test_cache_is_user_scoped():
    redis = FakeRedisService()
    service = MatchCacheService(cache_service=redis)
    session_id = "session-1"
    user_a = uuid4()
    user_b = uuid4()

    await service.cache_matches(user_a, session_id, [_match("A")])
    await service.cache_matches(user_b, session_id, [_match("B")])

    a_result = await service.get_paginated_matches(user_a, session_id, page=1, page_size=10)
    b_result = await service.get_paginated_matches(user_b, session_id, page=1, page_size=10)

    assert a_result is not None
    assert b_result is not None
    a_items, _ = a_result
    b_items, _ = b_result
    assert a_items[0]["title"] == "Job A"
    assert b_items[0]["title"] == "Job B"
    assert a_items[0]["description_html"] == "<p>Python backend role</p>"


@pytest.mark.asyncio
async def test_validate_match_session_checks_ownership():
    redis = FakeRedisService()
    service = MatchCacheService(cache_service=redis)
    owner = uuid4()
    other_user = uuid4()
    session_id = "session-2"

    await service.cache_matches(owner, session_id, [_match("Owner")])

    assert await service.validate_match_session(owner, session_id) is True
    assert await service.validate_match_session(other_user, session_id) is False


@pytest.mark.asyncio
async def test_resume_hash_mapping_roundtrip():
    redis = FakeRedisService()
    service = MatchCacheService(cache_service=redis)
    user_id = uuid4()
    resume_hash = "abc123"
    min_score = 0.5
    session_id = "session-3"

    ok = await service.cache_resume_session(user_id, resume_hash, min_score, session_id, ttl=60)
    cached = await service.get_cached_session_for_resume(user_id, resume_hash, min_score)

    assert ok is True
    assert cached == session_id


@pytest.mark.asyncio
async def test_resume_hash_key_changes_when_scoring_settings_change(monkeypatch):
    from app.infra import config as config_module

    redis = FakeRedisService()
    service = MatchCacheService(cache_service=redis)
    user_id = uuid4()
    settings = config_module.get_settings()

    await service.cache_resume_session(user_id, "abc123", 0.5, "session-a", ttl=60)

    monkeypatch.setattr(settings, "match_weight_semantic", 0.60)
    monkeypatch.setattr(settings, "match_weight_skill_title", 0.25)

    # Different settings must not resolve the earlier session.
    assert await service.get_cached_session_for_resume(user_id, "abc123", 0.5) is None
    await service.cache_resume_session(user_id, "abc123", 0.5, "session-b", ttl=60)
    assert await service.get_cached_session_for_resume(user_id, "abc123", 0.5) == "session-b"


@pytest.mark.asyncio
async def test_default_services_share_in_memory_cache(monkeypatch):
    monkeypatch.setattr("app.infra.cache.cache_service.get_settings", lambda: SimpleNamespace(redis_url=""))
    await close_cache_service()

    try:
        user_id = uuid4()
        writer = MatchCacheService()
        reader = MatchCacheService()

        ok = await writer.cache_resume_session(user_id, "abc123", 0.5, "session-4", ttl=60)
        cached = await reader.get_cached_session_for_resume(user_id, "abc123", 0.5)

        assert ok is True
        assert cached == "session-4"
    finally:
        await close_cache_service()
