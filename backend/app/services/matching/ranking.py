"""Vector candidate retrieval, hybrid reranking, and match response assembly."""

from __future__ import annotations

import logging
import uuid
from uuid import UUID

from fastapi import HTTPException
from pgvector.sqlalchemy import HALFVEC
from sqlalchemy import cast, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.models import Job
from app.infra.config import get_settings
from app.schemas.mappers import enum_to_str, job_to_match_result
from app.schemas.matching import MatchResponse, MatchResult, MatchSummaryResponse
from app.services.matching.cache import MatchCacheService
from app.services.matching.filters import apply_default_recency_filter
from app.services.matching.scoring import (
    clamp_01,
    explain_match,
    extract_resume_signals,
    hybrid_match_score,
    recency_score,
    skill_title_score,
    work_mode_score,
)

logger = logging.getLogger(__name__)


def match_results_from_cache(matches_data: list[dict[str, object]]) -> list[MatchResult]:
    return [MatchResult.model_validate(item) for item in matches_data]


def match_summaries(matches: list[MatchResult]) -> list[MatchSummaryResponse]:
    return [MatchSummaryResponse.model_validate(match.model_dump()) for match in matches]


async def rank_matches(
    db: AsyncSession, resume_embedding: list[float], resume_text: str, min_score: float
) -> tuple[list[MatchResult], bool]:
    """Run vector candidate retrieval + hybrid reranking.

    Returns (matched_results, used_fallback) where used_fallback is True
    when no results cleared the min_score and top-20 fallback was applied.
    """
    signals = extract_resume_signals(resume_text)
    settings = get_settings()

    await db.execute(text("SET LOCAL hnsw.ef_search = 100"))

    halfvec_resume_embedding = cast(resume_embedding, HALFVEC(1024))
    distance = Job.description_embedding.cosine_distance(halfvec_resume_embedding)
    stmt = (
        select(
            Job,
            (1 - distance).label("semantic_score"),
        )
        .where(Job.description_embedding.isnot(None))
        .where(Job.is_active.is_(True))
        .options(
            load_only(
                Job.id,
                Job.title,
                Job.company,
                Job.location,
                Job.city,
                Job.state,
                Job.country,
                Job.apply_url,
                Job.description_text,
                Job.job_category,
                Job.job_type,
                Job.work_mode,
                Job.posted_at,
            )
        )
        .order_by(distance)
        .limit(settings.match_rerank_pool)
    )

    try:
        result = await db.execute(stmt)
        candidate_rows: list[tuple[Job, float | None]] = [(job, semantic) for job, semantic in result.tuples().all()]
    except SQLAlchemyError as exc:
        message = str(exc)
        logger.exception("Match query failed: %s", message)
        if "different vector dimensions" in message.lower():
            raise HTTPException(
                status_code=500,
                detail=(
                    "Resume embedding dimension does not match stored job embeddings. "
                    "Re-embed job descriptions using the current embedding model."
                ),
            ) from exc
        raise HTTPException(
            status_code=500,
            detail="Matching query failed. Please try again later.",
        ) from exc

    ranked_rows: list[tuple[float, Job, dict[str, float]]] = []
    for job, semantic in candidate_rows:
        semantic_score = clamp_01(semantic)
        skill_title = skill_title_score(signals.tokens, job.title, job.description_text)
        work_mode = work_mode_score(enum_to_str(job.work_mode), signals)
        recency = recency_score(job.posted_at)
        final_score = hybrid_match_score(
            semantic_score=semantic_score,
            skill_title_score=skill_title,
            work_mode_score=work_mode,
            recency_score=recency,
        )
        ranked_rows.append(
            (
                final_score,
                job,
                explain_match(
                    semantic_score=semantic_score,
                    skill_title_score=skill_title,
                    work_mode_score=work_mode,
                    recency_score=recency,
                    final_score=final_score,
                ),
            )
        )

    ranked_rows.sort(key=lambda item: item[0], reverse=True)

    filtered_rows = [item for item in ranked_rows if item[0] >= min_score]
    used_fallback = False
    if not filtered_rows and ranked_rows:
        used_fallback = True
        filtered_rows = ranked_rows[: min(settings.match_fallback_count, len(ranked_rows))]

    if ranked_rows:
        top_score = ranked_rows[0][0]
        median_score = ranked_rows[len(ranked_rows) // 2][0]
        logger.info(
            "Match scoring: candidates=%s reranked=%s threshold=%.3f passed=%s fallback=%s top=%.3f median=%.3f",
            len(candidate_rows),
            len(ranked_rows),
            min_score,
            len([item for item in ranked_rows if item[0] >= min_score]),
            used_fallback,
            top_score,
            median_score,
        )
    else:
        logger.info(
            "Match scoring: candidates=0 reranked=0 threshold=%.3f passed=0 fallback=False",
            min_score,
        )

    return (
        [
            job_to_match_result(
                row,
                score=score,
                score_breakdown=explain,
            )
            for score, row, explain in filtered_rows
        ],
        used_fallback,
    )


async def return_cached_first_page(
    cache_service: MatchCacheService,
    user_id: UUID,
    cache_hash: str,
    min_score: float,
    page_size: int,
) -> MatchResponse | None:
    cached_session_id = await cache_service.get_cached_session_for_resume(user_id, cache_hash, min_score)
    if not cached_session_id:
        return None
    if not await cache_service.validate_match_session(user_id, cached_session_id):
        return None
    cached_page = await cache_service.get_paginated_matches(
        user_id,
        cached_session_id,
        page=1,
        page_size=page_size,
    )
    if cached_page is None:
        return None

    matches_data, total_count = cached_page
    matches = match_results_from_cache(matches_data)
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
    return MatchResponse(
        matches=match_summaries(matches),
        total=total_count,
        session_id=cached_session_id,
        page=1,
        page_size=page_size,
        total_pages=total_pages,
        reused_from_cache=True,
    )


async def build_match_response(
    *,
    db: AsyncSession,
    cache_service: MatchCacheService,
    user_id: UUID,
    cache_hash: str,
    min_score: float,
    page_size: int,
    resume_text: str,
    resume_embedding: list[float],
) -> MatchResponse:
    session_id = str(uuid.uuid4())
    matches, used_fallback = await rank_matches(db, resume_embedding, resume_text, min_score)
    matches = apply_default_recency_filter(matches)
    total_matches = len(matches)

    cache_success = False
    try:
        cache_success = await cache_service.cache_matches(user_id, session_id, matches)
        if cache_success:
            await cache_service.cache_resume_session(
                user_id,
                cache_hash,
                min_score,
                session_id,
            )
    except Exception as exc:  # noqa: BLE001  # cache failure should not fail the match response
        logger.warning(f"Failed to cache matches for session {session_id}: {exc}")

    total_pages = (total_matches + page_size - 1) // page_size if total_matches > 0 else 1
    first_page_matches = matches[:page_size]

    return MatchResponse(
        matches=match_summaries(first_page_matches),
        total=total_matches,
        session_id=session_id if cache_success else "",
        page=1,
        page_size=page_size,
        total_pages=total_pages,
        reused_from_cache=False,
        fallback=used_fallback,
    )
