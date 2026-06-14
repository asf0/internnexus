from __future__ import annotations

import hashlib
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import MatchResponse, MatchResult, MatchFacetsResponse, FacetItem, LocationFacetItem
from app.api.mappers import enum_to_str, job_to_match_result
from app.config import get_settings
from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models import Job, User, UserResume
from app.rate_limiter import limiter, RATE_LIMITS
from app.services.match_cache import MatchCacheService, get_match_cache_service
from app.services.posted_within import posted_within_cutoff
from app.services.query_embedding_service import QueryEmbeddingService
from app.utils.db import commit_or_500
from app.services.resume_service import (
    decrypt_resume_text,
    ResumeProcessingError,
    extract_resume_text,
    normalize_resume_text,
    resume_processing_client_message,
)

router = APIRouter()
logger = logging.getLogger(__name__)

_RESUME_SCHEMA_ERROR_DETAIL = (
    "Resume storage schema is outdated. Run database migrations (uv run alembic upgrade head) and retry."
)


def _is_resume_schema_error(exc: ProgrammingError) -> bool:
    message = str(getattr(exc, "orig", exc)).lower()
    return "user_resumes" in message and "content_hash" in message


def _map_resume_schema_commit_error(exc: SQLAlchemyError) -> HTTPException | None:
    if isinstance(exc, ProgrammingError) and _is_resume_schema_error(exc):
        return HTTPException(status_code=503, detail=_RESUME_SCHEMA_ERROR_DETAIL)
    return None


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
    posted_utc = posted_at if posted_at.tzinfo is not None else posted_at.replace(tzinfo=timezone.utc)
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


def _match_results_from_cache(matches_data: list[dict[str, object]]) -> list[MatchResult]:
    return [MatchResult.model_validate(item) for item in matches_data]


def _parse_filter_values(filter_value: str | None) -> list[str]:
    """Parse pipe-separated filter values into a list.

    Args:
        filter_value: Raw filter value from query parameter (may contain | delimiters)

    Returns:
        List of individual filter values, empty list if no valid values
    """
    if not filter_value:
        return []

    # Split by | and filter out empty strings
    values = [v.strip() for v in filter_value.split("|") if v.strip()]
    return values


def _filter_matches(
    matches: list[MatchResult],
    search: str | None = None,
    company: str | None = None,
    location: str | None = None,
    category: str | None = None,
    job_type: str | None = None,
    work_mode: str | None = None,
    posted_within: str | None = None,
) -> list[MatchResult]:
    """Filter match results based on provided criteria.

    Supports multiple values for filters (separated by |), using OR logic.
    For example, location="United States|Brazil" will match jobs in either location.
    """
    filtered = matches

    if search:
        search_lower = search.lower()
        filtered = [
            m
            for m in filtered
            if (
                search_lower in m.title.lower()
                or search_lower in m.company.lower()
                or search_lower in m.description_text.lower()
            )
        ]

    # Company filter with multiple values (OR logic)
    if company:
        company_values = _parse_filter_values(company)
        if company_values:
            company_values_lower = [v.lower() for v in company_values]
            filtered = [m for m in filtered if any(v in m.company.lower() for v in company_values_lower)]

    # Location filter with multiple values (OR logic)
    if location:
        location_values = _parse_filter_values(location)
        if location_values:
            location_values_lower = [v.lower() for v in location_values]
            filtered = [
                m
                for m in filtered
                if any(
                    v in m.location.lower()
                    or (m.city and v in m.city.lower())
                    or (m.state and v in m.state.lower())
                    or (m.country and v in m.country.lower())
                    for v in location_values_lower
                )
            ]

    # Category filter with multiple values (OR logic)
    if category:
        category_values = _parse_filter_values(category)
        if category_values:
            category_values_lower = [v.lower() for v in category_values]
            filtered = [
                m
                for m in filtered
                if m.job_category and any(v in m.job_category.lower() for v in category_values_lower)
            ]

    # Job type filter with multiple values (OR logic)
    if job_type:
        job_type_values = _parse_filter_values(job_type)
        if job_type_values:
            job_type_values_lower = [v.lower() for v in job_type_values]
            filtered = [
                m for m in filtered if m.job_type and any(v in m.job_type.lower() for v in job_type_values_lower)
            ]

    # Work mode filter with multiple values (OR logic)
    if work_mode:
        work_mode_values = _parse_filter_values(work_mode)
        if work_mode_values:
            work_mode_values_lower = [v.lower() for v in work_mode_values]
            filtered = [
                m for m in filtered if m.work_mode and any(v in m.work_mode.lower() for v in work_mode_values_lower)
            ]

    if posted_within:
        cutoff = posted_within_cutoff(posted_within, datetime.now(timezone.utc))
        if cutoff:
            filtered = [m for m in filtered if m.posted_at and m.posted_at >= cutoff]

    return filtered


async def _rank_matches(
    db: AsyncSession, resume_embedding: list[float], resume_text: str, min_score: float
) -> list[MatchResult]:
    """Run vector candidate retrieval + hybrid reranking."""
    signals = _extract_resume_signals(resume_text)

    stmt = (
        select(
            Job,
            (1 - Job.description_embedding.cosine_distance(resume_embedding)).label("semantic_score"),
        )
        .where(Job.description_embedding.isnot(None))
        .where(Job.is_active.is_(True))
        .order_by((1 - Job.description_embedding.cosine_distance(resume_embedding)).desc())
        .limit(_MAX_CANDIDATES)
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
    for job, semantic in candidate_rows[:_RERANK_POOL]:
        semantic_score = _clamp_01(semantic)
        skill_title = _skill_title_score(signals.tokens, job.title, job.description_text)
        work_mode = _work_mode_score(enum_to_str(job.work_mode), signals)
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
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
    return MatchResponse(
        matches=_match_results_from_cache(matches_data),
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
    except Exception as exc:  # noqa: BLE001  # cache failure should not fail the match response
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
        logger.info("Resume match upload rejected for user %s: %s", current_user.id, exc)
        raise HTTPException(status_code=400, detail=resume_processing_client_message(exc)) from exc

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
    except Exception as exc:  # noqa: BLE001  # embedding provider failures are surfaced as 503 to the client
        logger.exception("Failed to generate embedding for uploaded resume")
        raise HTTPException(
            status_code=503,
            detail="Embedding service unavailable. Please try again later.",
        ) from exc

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
        resume_result = await db.execute(select(UserResume).where(UserResume.user_id == current_user.id))
    except ProgrammingError as exc:
        if _is_resume_schema_error(exc):
            raise HTTPException(status_code=503, detail=_RESUME_SCHEMA_ERROR_DETAIL) from exc
        raise
    user_resume = resume_result.scalar_one_or_none()
    if user_resume is None:
        raise HTTPException(status_code=400, detail="No profile resume found. Upload one in your profile first.")

    if not user_resume.content_hash:
        raise HTTPException(status_code=400, detail="Stored resume is incomplete. Please upload again.")

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
    if user_resume.embedding_dim and user_resume.embedding_dim != settings.embedding_dimensions:
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
            logger.exception("Failed to decrypt stored resume for user %s", current_user.id)
            user_resume.status = "error"
            user_resume.embedding_error = "Failed to decrypt stored resume"
            await commit_or_500(
                db,
                operation="record resume decrypt failure",
                detail="Failed to update resume status",
                error_mapper=_map_resume_schema_commit_error,
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to decrypt stored resume. Please upload again.",
            ) from exc

        try:
            embedder = QueryEmbeddingService()
            resume_embedding = await embedder.embed(resume_text)
        except Exception as exc:  # noqa: BLE001  # embedding provider failures are surfaced as 503 to the client
            logger.exception("Failed to generate embedding for stored resume")
            user_resume.status = "error"
            user_resume.embedding_error = "Embedding service unavailable"
            await commit_or_500(
                db,
                operation="record resume embedding failure",
                detail="Failed to update resume status",
                error_mapper=_map_resume_schema_commit_error,
            )
            raise HTTPException(
                status_code=503,
                detail="Embedding service unavailable. Please try again later.",
            ) from exc

        user_resume.resume_embedding = resume_embedding
        user_resume.embedding_model = settings.embedding_model
        user_resume.embedding_dim = len(resume_embedding)
        user_resume.last_embedded_at = datetime.now(timezone.utc)
        user_resume.status = "ready"
        user_resume.embedding_error = None
        await commit_or_500(db, operation="store re-embedded resume")
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
    search: str | None = Query(None, description="Search in title, company, description"),
    company: str | None = Query(None, description="Filter by company name"),
    location: str | None = Query(None, description="Filter by location"),
    category: str | None = Query(None, description="Filter by job category"),
    job_type: str | None = Query(None, description="Filter by job type"),
    work_mode: str | None = Query(None, description="Filter by work mode"),
    posted_within: str | None = Query(None, description="Filter by posting date (24h, 7d, 30d)"),
) -> MatchResponse:
    """Retrieve a specific page of cached match results with optional filters.

    Args:
        session_id: The match session ID from POST /match
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        search: Optional search text to filter matches
        company: Optional company name filter
        location: Optional location filter
        category: Optional job category filter
        job_type: Optional job type filter
        work_mode: Optional work mode filter
        posted_within: Optional date filter (24h, 7d, 30d)

    Returns:
        MatchResponse with filtered and paginated matches

    Raises:
        HTTPException 404: If session not found or expired
        HTTPException 400: If pagination params invalid
    """
    # Validate session ownership then retrieve all matches from cache.
    if not await cache_service.validate_match_session(current_user.id, session_id):
        raise HTTPException(status_code=404, detail="Match session not found or expired")

    # Get ALL matches from cache (not paginated yet)
    all_matches_data = await cache_service.get_all_matches(current_user.id, session_id)

    if all_matches_data is None:
        raise HTTPException(status_code=404, detail="Match session not found or expired")

    # Convert to MatchResult objects
    all_matches = _match_results_from_cache(all_matches_data)

    # Apply filters
    filtered_matches = _filter_matches(
        all_matches,
        search=search,
        company=company,
        location=location,
        category=category,
        job_type=job_type,
        work_mode=work_mode,
        posted_within=posted_within,
    )

    # Calculate pagination on filtered results
    total_count = len(filtered_matches)
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_matches = filtered_matches[start_idx:end_idx]

    # Return MatchResponse with filtered results
    return MatchResponse(
        matches=paginated_matches,
        total=total_count,
        session_id=session_id,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        reused_from_cache=False,
    )


def _calculate_facets(matches: list[MatchResult]) -> MatchFacetsResponse:
    """Calculate facet values and counts from a list of matches.

    Args:
        matches: List of MatchResult objects to analyze

    Returns:
        MatchFacetsResponse with companies, categories, job_types, work_modes, and locations
    """
    # Count companies
    company_counts: dict[str, int] = {}
    for match in matches:
        company = match.company
        company_counts[company] = company_counts.get(company, 0) + 1

    companies = [
        FacetItem(value=company, label=company, count=count)
        for company, count in sorted(company_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    # Count categories
    category_counts: dict[str, int] = {}
    for match in matches:
        if match.job_category:
            category_counts[match.job_category] = category_counts.get(match.job_category, 0) + 1

    categories = [
        FacetItem(value=cat, label=cat, count=count)
        for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    # Count job types
    job_type_counts: dict[str, int] = {}
    for match in matches:
        if match.job_type:
            job_type_counts[match.job_type] = job_type_counts.get(match.job_type, 0) + 1

    job_types = [
        FacetItem(value=jt, label=jt, count=count)
        for jt, count in sorted(job_type_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    # Count work modes
    work_mode_counts: dict[str, int] = {}
    for match in matches:
        if match.work_mode:
            work_mode_counts[match.work_mode] = work_mode_counts.get(match.work_mode, 0) + 1

    work_modes = [
        FacetItem(value=wm, label=wm, count=count)
        for wm, count in sorted(work_mode_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    # Build location hierarchy
    locations = _build_location_hierarchy(matches)

    return MatchFacetsResponse(
        companies=companies,
        categories=categories,
        job_types=job_types,
        work_modes=work_modes,
        locations=locations,
        total_matches=len(matches),
    )


def _build_location_hierarchy(matches: list[MatchResult]) -> list[LocationFacetItem]:
    """Build location hierarchy from match location data.

    Args:
        matches: List of MatchResult objects

    Returns:
        Hierarchical list of LocationFacetItem objects
    """
    # Track counts per location path
    country_counts: dict[str, int] = {}
    state_counts: dict[tuple[str, str], int] = {}  # (country, state) -> count
    city_counts: dict[tuple[str, str | None, str], int] = {}  # (country, state, city) -> count

    for match in matches:
        country = match.country
        state = match.state
        city = match.city

        if country:
            country_counts[country] = country_counts.get(country, 0) + 1

        if country and state:
            state_key = (country, state)
            state_counts[state_key] = state_counts.get(state_key, 0) + 1

        if country and city:
            city_key = (country, state, city)
            city_counts[city_key] = city_counts.get(city_key, 0) + 1

    # Build hierarchy
    locations: list[LocationFacetItem] = []

    for country, country_count in sorted(country_counts.items(), key=lambda x: x[1], reverse=True):
        # Get states for this country
        country_states = [(state, count) for (c, state), count in state_counts.items() if c == country]

        state_items: list[LocationFacetItem] = []
        for state, state_count in sorted(country_states, key=lambda x: x[1], reverse=True):
            # Get cities for this state
            state_cities = [(city, count) for (c, s, city), count in city_counts.items() if c == country and s == state]

            city_items: list[LocationFacetItem] = []
            for city, city_count in sorted(state_cities, key=lambda x: x[1], reverse=True):
                city_items.append(
                    LocationFacetItem(
                        value=city,
                        label=city,
                        count=city_count,
                        type="city",
                        country=country,
                        state=state,
                        children=None,
                    )
                )

            state_items.append(
                LocationFacetItem(
                    value=state,
                    label=state,
                    count=state_count,
                    type="state",
                    country=country,
                    state=state,
                    children=city_items if city_items else None,
                )
            )

        locations.append(
            LocationFacetItem(
                value=country,
                label=country,
                count=country_count,
                type="country",
                country=country,
                state=None,
                children=state_items if state_items else None,
            )
        )

    return locations


@router.get("/match/{session_id}/facets", response_model=MatchFacetsResponse)
@limiter.limit(RATE_LIMITS["match"])
async def get_match_facets(
    request: Request,
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    cache_service: MatchCacheService = Depends(get_match_cache_service),
    search: str | None = Query(None, description="Search in title, company, description"),
    company: str | None = Query(None, description="Filter by company name"),
    location: str | None = Query(None, description="Filter by location"),
    category: str | None = Query(None, description="Filter by job category"),
    job_type: str | None = Query(None, description="Filter by job type"),
    work_mode: str | None = Query(None, description="Filter by work mode"),
    posted_within: str | None = Query(None, description="Filter by posting date (24h, 7d, 30d)"),
) -> MatchFacetsResponse:
    """Get dynamic facets (filter options with counts) for cached match results.

    Calculates facets based on the current filter state. For example, if location
    is set to "United States", only companies with jobs in the US will be returned.

    Args:
        session_id: The match session ID from POST /match
        search: Optional search text to filter matches
        company: Optional company name filter
        location: Optional location filter
        category: Optional job category filter
        job_type: Optional job type filter
        work_mode: Optional work mode filter
        posted_within: Optional date filter (24h, 7d, 30d)

    Returns:
        MatchFacetsResponse with companies, categories, job_types, work_modes, and locations

    Raises:
        HTTPException 404: If session not found or expired
    """
    # Validate session ownership then retrieve all matches from cache.
    if not await cache_service.validate_match_session(current_user.id, session_id):
        raise HTTPException(status_code=404, detail="Match session not found or expired")

    # Get ALL matches from cache
    all_matches_data = await cache_service.get_all_matches(current_user.id, session_id)

    if all_matches_data is None:
        raise HTTPException(status_code=404, detail="Match session not found or expired")

    # Convert to MatchResult objects
    all_matches = _match_results_from_cache(all_matches_data)

    # Apply filters to get the subset of matches that match current criteria
    filtered_matches = _filter_matches(
        all_matches,
        search=search,
        company=company,
        location=location,
        category=category,
        job_type=job_type,
        work_mode=work_mode,
        posted_within=posted_within,
    )

    # Calculate facets from filtered matches
    return _calculate_facets(filtered_matches)
