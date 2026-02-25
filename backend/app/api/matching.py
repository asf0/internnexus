from __future__ import annotations

import hashlib
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import MatchResponse, MatchResult
from app.api.mappers import job_to_match_result
from app.config import get_settings
from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models import Job, User, UserResume
from app.rate_limiter import limiter, RATE_LIMITS
from app.services.match_cache import MatchCacheService, get_match_cache_service
from app.services.query_embedding_service import QueryEmbeddingService
from app.services.resume_service import (
    decrypt_resume_text,
    ResumeProcessingError,
    extract_resume_text,
    normalize_resume_text,
)

router = APIRouter()
logger = logging.getLogger(__name__)

_RESUME_SCHEMA_ERROR_DETAIL = (
    "Resume storage schema is outdated. Run database migrations "
    "(uv run alembic upgrade head) and retry."
)


def _is_resume_schema_error(exc: ProgrammingError) -> bool:
    message = str(getattr(exc, "orig", exc)).lower()
    return "user_resumes" in message and "content_hash" in message


_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+#\.\-]{1,}")
_STOPWORDS = {
    "and",
    "the",
    "for",
    "with",
    "that",
    "this",
    "from",
    "you",
    "your",
    "are",
    "was",
    "were",
    "have",
    "has",
    "will",
    "our",
    "not",
    "all",
    "any",
}
_WEIGHT_SEMANTIC = 0.70
_WEIGHT_SKILL_TITLE = 0.15
_WEIGHT_WORK_MODE = 0.08
_WEIGHT_RECENCY = 0.07
_MAX_CANDIDATES = 3000
_RERANK_POOL = 1000
_FALLBACK_COUNT = 20


@dataclass
class ResumeSignals:
    tokens: set[str]
    prefers_remote: bool
    prefers_hybrid: bool
    prefers_onsite: bool


def _clamp_01(value: float | None) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(1.0, float(value)))


def _tokenize(text: str, limit: int = 300) -> set[str]:
    if not text:
        return set()
    tokens = {
        token.lower()
        for token in _TOKEN_RE.findall(text)
        if token and token.lower() not in _STOPWORDS and len(token) > 2
    }
    if len(tokens) <= limit:
        return tokens
    return set(sorted(tokens)[:limit])


def _extract_resume_signals(resume_text: str) -> ResumeSignals:
    lowered = resume_text.lower()
    return ResumeSignals(
        tokens=_tokenize(resume_text, limit=500),
        prefers_remote="remote" in lowered,
        prefers_hybrid="hybrid" in lowered,
        prefers_onsite=("on-site" in lowered or "onsite" in lowered or "on site" in lowered),
    )


def _overlap_ratio(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, min(len(a), len(b)))


def _skill_title_score(
    resume_tokens: set[str],
    title: str,
    description_text: str | None,
) -> float:
    title_tokens = _tokenize(title, limit=60)
    description_tokens = _tokenize(description_text or "", limit=300)
    title_overlap = _overlap_ratio(resume_tokens, title_tokens)
    description_overlap = _overlap_ratio(resume_tokens, description_tokens)
    return _clamp_01(0.65 * title_overlap + 0.35 * description_overlap)


def _work_mode_score(work_mode: str | None, signals: ResumeSignals) -> float:
    raw_mode = work_mode
    mode = str(raw_mode or "").strip().lower()
    explicit_preference = signals.prefers_remote or signals.prefers_hybrid or signals.prefers_onsite
    if not explicit_preference:
        return 0.5
    if not mode:
        return 0.5
    if signals.prefers_remote:
        if mode == "remote":
            return 1.0
        if mode == "hybrid":
            return 0.7
        return 0.2
    if signals.prefers_hybrid:
        if mode == "hybrid":
            return 1.0
        if mode == "remote":
            return 0.7
        return 0.4
    if signals.prefers_onsite:
        if mode in {"on-site", "onsite", "on site"}:
            return 1.0
        if mode == "hybrid":
            return 0.7
        return 0.3
    return 0.5


def _recency_score(posted_at: datetime | None) -> float:
    if posted_at is None:
        return 0.4
    now = datetime.now(timezone.utc)
    posted_utc = (
        posted_at if posted_at.tzinfo is not None else posted_at.replace(tzinfo=timezone.utc)
    )
    age_days = max(0.0, (now - posted_utc).total_seconds() / 86400.0)
    # Linear decay to 0 at 120 days.
    return _clamp_01(1.0 - (age_days / 120.0))


def _hybrid_match_score(
    *,
    semantic_score: float,
    skill_title_score: float,
    work_mode_score: float,
    recency_score: float,
) -> float:
    return _clamp_01(
        (_WEIGHT_SEMANTIC * _clamp_01(semantic_score))
        + (_WEIGHT_SKILL_TITLE * _clamp_01(skill_title_score))
        + (_WEIGHT_WORK_MODE * _clamp_01(work_mode_score))
        + (_WEIGHT_RECENCY * _clamp_01(recency_score))
    )


def _explain_match(
    *,
    semantic_score: float,
    skill_title_score: float,
    work_mode_score: float,
    recency_score: float,
    final_score: float,
) -> dict[str, float]:
    return {
        "semantic": round(_clamp_01(semantic_score), 4),
        "skill_title": round(_clamp_01(skill_title_score), 4),
        "work_mode": round(_clamp_01(work_mode_score), 4),
        "recency": round(_clamp_01(recency_score), 4),
        "final": round(_clamp_01(final_score), 4),
    }


async def _rank_matches(
    db: AsyncSession, resume_embedding: list[float], resume_text: str, min_score: float
) -> list[MatchResult]:
    """Run vector candidate retrieval + hybrid reranking."""
    signals = _extract_resume_signals(resume_text)

    stmt = (
        select(
            Job,
            (1 - Job.description_embedding.cosine_distance(resume_embedding)).label(
                "semantic_score"
            ),
        )
        .where(Job.description_embedding.isnot(None))
        .where(Job.is_active.is_(True))
        .order_by((1 - Job.description_embedding.cosine_distance(resume_embedding)).desc())
        .limit(_MAX_CANDIDATES)
    )

    try:
        result = await db.execute(stmt)
        candidate_rows = cast(list[tuple[Job, float | None]], result.tuples().all())
    except Exception as exc:
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
    for job, semantic in candidate_rows[:_RERANK_POOL]:
        semantic_score = _clamp_01(semantic)
        skill_title = _skill_title_score(signals.tokens, job.title, job.description_text)
        work_mode = _work_mode_score(job.work_mode.value if job.work_mode else None, signals)
        recency = _recency_score(job.posted_at)
        final_score = _hybrid_match_score(
            semantic_score=semantic_score,
            skill_title_score=skill_title,
            work_mode_score=work_mode,
            recency_score=recency,
        )
        ranked_rows.append(
            (
                final_score,
                job,
                _explain_match(
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
        filtered_rows = ranked_rows[: min(_FALLBACK_COUNT, len(ranked_rows))]

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

    return [
        job_to_match_result(
            row,
            score=score,
            score_breakdown=explain,
        )
        for score, row, explain in filtered_rows
    ]


async def _return_cached_first_page(
    cache_service: MatchCacheService,
    user_id: UUID,
    cache_hash: str,
    min_score: float,
    page_size: int,
) -> MatchResponse | None:
    cached_session_id = await cache_service.get_cached_session_for_resume(
        user_id, cache_hash, min_score
    )
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
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
    return MatchResponse(
        matches=[MatchResult(**item) for item in matches_data],
        total=total_count,
        session_id=cached_session_id,
        page=1,
        page_size=page_size,
        total_pages=total_pages,
        reused_from_cache=True,
    )


async def _build_match_response(
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
    matches = await _rank_matches(db, resume_embedding, resume_text, min_score)
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
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Failed to cache matches for session {session_id}: {exc}")

    total_pages = (total_matches + page_size - 1) // page_size if total_matches > 0 else 1
    first_page_matches = matches[:page_size]

    return MatchResponse(
        matches=first_page_matches,
        total=total_matches,
        session_id=session_id if cache_success else "",
        page=1,
        page_size=page_size,
        total_pages=total_pages,
        reused_from_cache=False,
    )


@router.post("/match", response_model=MatchResponse)
@limiter.limit(RATE_LIMITS["match"])
async def match_resume(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    cache_service: MatchCacheService = Depends(get_match_cache_service),
    min_score: float = 0.5,
    page_size: int = 20,
) -> MatchResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_content = file.file.read()
    if len(file_content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    try:
        extracted_text = extract_resume_text(file.filename, file_content)
    except ResumeProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    resume_text = normalize_resume_text(extracted_text)
    if not resume_text:
        raise HTTPException(status_code=400, detail="Resume text is empty after normalization")

    min_score = max(0.0, min(min_score, 1.0))
    page_size = max(1, min(page_size, 100))

    file_hash = hashlib.sha256(file_content).hexdigest()
    cached_response = await _return_cached_first_page(
        cache_service=cache_service,
        user_id=current_user.id,
        cache_hash=file_hash,
        min_score=min_score,
        page_size=page_size,
    )
    if cached_response:
        return cached_response

    try:
        embedder = QueryEmbeddingService()
        resume_embedding = await embedder.embed(resume_text)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Embedding service unavailable: {str(exc)}")

    return await _build_match_response(
        db=db,
        cache_service=cache_service,
        user_id=current_user.id,
        cache_hash=file_hash,
        min_score=min_score,
        page_size=page_size,
        resume_text=resume_text,
        resume_embedding=resume_embedding,
    )


@router.post("/match/profile", response_model=MatchResponse)
@limiter.limit(RATE_LIMITS["match"])
async def match_profile_resume(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    cache_service: MatchCacheService = Depends(get_match_cache_service),
    min_score: float = 0.5,
    page_size: int = 20,
) -> MatchResponse:
    min_score = max(0.0, min(min_score, 1.0))
    page_size = max(1, min(page_size, 100))

    try:
        resume_result = await db.execute(
            select(UserResume).where(UserResume.user_id == current_user.id)
        )
    except ProgrammingError as exc:
        if _is_resume_schema_error(exc):
            raise HTTPException(status_code=503, detail=_RESUME_SCHEMA_ERROR_DETAIL) from exc
        raise
    user_resume = resume_result.scalar_one_or_none()
    if user_resume is None:
        raise HTTPException(
            status_code=400, detail="No profile resume found. Upload one in your profile first."
        )

    if not user_resume.content_hash:
        raise HTTPException(
            status_code=400, detail="Stored resume is incomplete. Please upload again."
        )

    cached_response = await _return_cached_first_page(
        cache_service=cache_service,
        user_id=current_user.id,
        cache_hash=user_resume.content_hash,
        min_score=min_score,
        page_size=page_size,
    )
    if cached_response:
        return cached_response

    resume_text = ""
    needs_reembed = False
    settings = get_settings()
    if user_resume.embedding_model != settings.embedding_model:
        needs_reembed = True
    if user_resume.embedding_dim and user_resume.embedding_dim != 1024:
        needs_reembed = True
    if user_resume.resume_embedding is None:
        needs_reembed = True

    if needs_reembed:
        if not user_resume.encrypted_resume_text:
            raise HTTPException(
                status_code=400,
                detail="Stored resume cannot be re-embedded. Please upload your resume again.",
            )
        try:
            resume_text = decrypt_resume_text(user_resume.encrypted_resume_text)
        except ResumeProcessingError as exc:
            user_resume.status = "error"
            user_resume.embedding_error = str(exc)
            await db.commit()
            raise HTTPException(
                status_code=500,
                detail="Failed to decrypt stored resume. Please upload again.",
            ) from exc

        try:
            embedder = QueryEmbeddingService()
            resume_embedding = await embedder.embed(resume_text)
        except Exception as exc:  # noqa: BLE001
            user_resume.status = "error"
            user_resume.embedding_error = str(exc)
            await db.commit()
            raise HTTPException(
                status_code=503, detail=f"Embedding service unavailable: {exc}"
            ) from exc

        user_resume.resume_embedding = resume_embedding
        user_resume.embedding_model = settings.embedding_model
        user_resume.embedding_dim = len(resume_embedding)
        user_resume.last_embedded_at = datetime.now(timezone.utc)
        user_resume.status = "ready"
        user_resume.embedding_error = None
        await db.commit()
    else:
        if user_resume.resume_embedding is None:
            raise HTTPException(
                status_code=400,
                detail="Stored resume has no embedding. Please upload your resume again.",
            )
        resume_embedding = list(user_resume.resume_embedding)
        if user_resume.encrypted_resume_text:
            resume_text = decrypt_resume_text(user_resume.encrypted_resume_text)
        else:
            resume_text = ""

    if not resume_text:
        raise HTTPException(
            status_code=400,
            detail="Stored resume text is unavailable. Please upload your resume again.",
        )

    return await _build_match_response(
        db=db,
        cache_service=cache_service,
        user_id=current_user.id,
        cache_hash=user_resume.content_hash,
        min_score=min_score,
        page_size=page_size,
        resume_text=resume_text,
        resume_embedding=resume_embedding,
    )


@router.get("/match/{session_id}", response_model=MatchResponse)
@limiter.limit(RATE_LIMITS["match"])
async def get_match_page(
    request: Request,
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    cache_service: MatchCacheService = Depends(get_match_cache_service),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> MatchResponse:
    """Retrieve a specific page of cached match results.

    Args:
        session_id: The match session ID from POST /match
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)

    Returns:
        MatchResponse with paginated matches

    Raises:
        HTTPException 404: If session not found or expired
        HTTPException 400: If pagination params invalid
    """
    # Validate session ownership then retrieve paginated matches from cache.
    if not await cache_service.validate_match_session(current_user.id, session_id):
        raise HTTPException(status_code=404, detail="Match session not found or expired")

    result = await cache_service.get_paginated_matches(current_user.id, session_id, page, page_size)

    # If result is None (session expired/not found), raise HTTPException 404
    if result is None:
        raise HTTPException(status_code=404, detail="Match session not found or expired")

    # Unpack result: matches_data, total_count
    matches_data, total_count = result

    # Convert matches_data (list of dicts) back to MatchResult objects
    matches = [MatchResult(**match_dict) for match_dict in matches_data]

    # Calculate total_pages
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

    # Return MatchResponse with all required fields
    return MatchResponse(
        matches=matches,
        total=total_count,
        session_id=session_id,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        reused_from_cache=False,
    )
