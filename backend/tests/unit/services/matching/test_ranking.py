from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.matching.ranking import return_cached_first_page


def _cached_match(index: int) -> dict[str, object]:
    return {
        "job_id": str(uuid4()),
        "score": 0.8,
        "match_percentage": 80.0,
        "title": f"Job {index}",
        "company": "Example",
        "location": "Remote",
        "apply_url": "https://example.com/apply",
        "description_html": "<p>Description</p>",
        "posted_at": datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat(),
    }


@pytest.mark.asyncio
async def test_cached_first_page_preserves_page_and_full_total() -> None:
    cache = AsyncMock()
    cache.get_cached_session_for_resume.return_value = "session-1"
    cache.validate_match_session.return_value = True
    cache.get_paginated_matches.return_value = ([_cached_match(index) for index in range(20)], 45)

    response = await return_cached_first_page(
        cache_service=cache,
        user_id=uuid4(),
        cache_hash="resume-hash",
        min_score=0.5,
        page_size=20,
    )

    assert response is not None
    assert len(response.matches) == 20
    assert response.total == 45
    assert response.total_pages == 3
    assert "description_text" not in response.matches[0].model_dump()
