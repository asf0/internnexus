from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.dialects import postgresql
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.services.matching.ranking import rank_matches
from app.services.matching.scoring import (
    extract_resume_signals,
    hybrid_match_score,
    recency_score,
    skill_title_score,
    work_mode_score,
)


def test_skill_title_score_favors_overlap():
    resume = "Python FastAPI PostgreSQL Redis machine learning"
    signals = extract_resume_signals(resume)

    high = skill_title_score(
        signals.tokens,
        title="Python Backend Engineer",
        description_text="Build APIs with FastAPI, Redis and PostgreSQL",
    )
    low = skill_title_score(
        signals.tokens,
        title="Graphic Designer",
        description_text="Create visual assets and branding collateral",
    )

    assert high > low
    assert 0.0 <= high <= 1.0
    assert 0.0 <= low <= 1.0


def test_work_mode_score_respects_explicit_remote_preference():
    signals = extract_resume_signals("Looking for remote backend engineering roles.")
    remote = work_mode_score("remote", signals)
    onsite = work_mode_score("on-site", signals)

    assert remote > onsite


def test_recency_score_newer_jobs_rank_higher():
    now = datetime.now(timezone.utc)
    recent = recency_score(now - timedelta(days=5))
    old = recency_score(now - timedelta(days=140))

    assert recent > old
    assert 0.0 <= recent <= 1.0
    assert 0.0 <= old <= 1.0


def test_hybrid_score_weights_semantic_heavily():
    strong_semantic = hybrid_match_score(
        semantic_score=0.9,
        skill_title_score=0.3,
        work_mode_score=0.3,
        recency_score=0.3,
    )
    weak_semantic = hybrid_match_score(
        semantic_score=0.3,
        skill_title_score=0.9,
        work_mode_score=0.9,
        recency_score=0.9,
    )

    assert strong_semantic > weak_semantic


def test_hybrid_score_reads_nondefault_weights_from_settings(monkeypatch):
    from app.infra import config as config_module

    settings = config_module.get_settings()
    monkeypatch.setattr(settings, "match_weight_semantic", 1.0)
    monkeypatch.setattr(settings, "match_weight_skill_title", 0.0)
    monkeypatch.setattr(settings, "match_weight_work_mode", 0.0)
    monkeypatch.setattr(settings, "match_weight_recency", 0.0)

    assert hybrid_match_score(
        semantic_score=0.5,
        skill_title_score=1.0,
        work_mode_score=1.0,
        recency_score=1.0,
    ) == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_rank_matches_returns_500_on_sqlalchemy_error():
    db = AsyncMock()
    db.execute.side_effect = [None, SQLAlchemyError("vector dimension mismatch")]

    with pytest.raises(HTTPException) as exc_info:
        await rank_matches(db, resume_embedding=[0.1] * 1024, resume_text="Python backend", min_score=0.0)

    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_rank_matches_casts_both_vectors_to_halfvec_for_hnsw():
    class _Result:
        def tuples(self):
            return self

        def all(self):
            return []

    class _Db:
        def __init__(self):
            self.statements = []

        async def execute(self, statement):
            self.statements.append(statement)
            return _Result()

    db = _Db()
    await rank_matches(db, resume_embedding=[0.1] * 1024, resume_text="Python backend", min_score=0.0)

    sql = str(db.statements[1].compile(dialect=postgresql.dialect()))
    assert "jobs.description_embedding" in sql
    assert "CAST(%(param_2)s AS HALFVEC(1024))" in sql
