from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.api.schemas import MatchResult
from app.services.match_cache import MatchCacheService


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
        description_text="Python backend role",
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
