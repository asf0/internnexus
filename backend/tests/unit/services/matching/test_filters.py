from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.matching import MatchResult
from app.services.matching.filters import filter_matches


def test_search_matches_sanitized_description_html() -> None:
    match = MatchResult(
        job_id=uuid4(),
        score=0.8,
        match_percentage=80,
        title="Platform Engineer",
        company="Example Co",
        location="Remote",
        apply_url="https://example.com/apply",
        description_html="<p>Build reliable distributed systems.</p>",
        posted_at=datetime.now(timezone.utc),
    )

    assert filter_matches([match], search="distributed") == [match]
