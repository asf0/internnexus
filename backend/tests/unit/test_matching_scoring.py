from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.api.matching import (
    _extract_resume_signals,
    _hybrid_match_score,
    _rank_matches,
    _recency_score,
    _skill_title_score,
    _work_mode_score,
)


def test_skill_title_score_favors_overlap():
    resume = "Python FastAPI PostgreSQL Redis machine learning"
    signals = _extract_resume_signals(resume)

    high = _skill_title_score(
        signals.tokens,
        title="Python Backend Engineer",
        description_text="Build APIs with FastAPI, Redis and PostgreSQL",
    )
    low = _skill_title_score(
        signals.tokens,
        title="Graphic Designer",
        description_text="Create visual assets and branding collateral",
    )

    assert high > low
    assert 0.0 <= high <= 1.0
    assert 0.0 <= low <= 1.0


def test_work_mode_score_respects_explicit_remote_preference():
    signals = _extract_resume_signals("Looking for remote backend engineering roles.")
    remote = _work_mode_score("remote", signals)
    onsite = _work_mode_score("on-site", signals)

    assert remote > onsite


def test_recency_score_newer_jobs_rank_higher():
    now = datetime.now(timezone.utc)
    recent = _recency_score(now - timedelta(days=5))
    old = _recency_score(now - timedelta(days=140))

    assert recent > old
    assert 0.0 <= recent <= 1.0
    assert 0.0 <= old <= 1.0


def test_hybrid_score_weights_semantic_heavily():
    strong_semantic = _hybrid_match_score(
        semantic_score=0.9,
        skill_title_score=0.3,
        work_mode_score=0.3,
        recency_score=0.3,
    )
    weak_semantic = _hybrid_match_score(
        semantic_score=0.3,
        skill_title_score=0.9,
        work_mode_score=0.9,
        recency_score=0.9,
    )

    assert strong_semantic > weak_semantic


@pytest.mark.asyncio
async def test_rank_matches_returns_500_on_sqlalchemy_error():
    db = AsyncMock()
    db.execute.side_effect = SQLAlchemyError("vector dimension mismatch")

    with pytest.raises(HTTPException) as exc_info:
        await _rank_matches(db, resume_embedding=[0.1] * 2560, resume_text="Python backend", min_score=0.0)

    assert exc_info.value.status_code == 500
