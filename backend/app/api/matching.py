"""Resume-matching routes. Scoring, ranking and faceting live in app/services/matching/."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.matching import MatchFacetsResponse, MatchResponse
from app.infra.config import get_settings
from app.auth.dependencies import get_current_user
from app.infra.db import get_db
from app.models import User, UserResume
from app.infra.rate_limiter import limiter, RATE_LIMITS
from app.services.jobs.search import MAX_PAGINATION_OFFSET
from app.services.matching.cache import MatchCacheService, get_match_cache_service
from app.services.matching.facets import calculate_facets
from app.services.matching.filters import filter_matches
from app.services.matching.ranking import (
    build_match_response,
    match_results_from_cache,
    match_summaries,
    return_cached_first_page,
)
from app.services.users.query_embedding import QueryEmbeddingService
from app.infra.commit import commit_or_500
from app.services.users.resume import (
    decrypt_resume_text,
    ResumeProcessingError,
    RESUME_SCHEMA_ERROR_DETAIL,
    extract_resume_text,
    is_resume_schema_error,
    map_resume_schema_commit_error,
    normalize_resume_text,
    read_resume_upload,
    resume_processing_client_message,
)

router = APIRouter()
logger = logging.getLogger(__name__)

_MATCH_SESSION_NOT_FOUND = "Match session not found or expired"


def _clamp_match_params(min_score: float, page_size: int) -> tuple[float, int]:
    """Clamp user-supplied scoring/pagination params to supported ranges."""
    return max(0.0, min(min_score, 1.0)), max(1, min(page_size, 100))


async def _filtered_session_matches(
    cache_service: MatchCacheService,
    user_id: UUID,
    session_id: str,
    **filters: str | None,
) -> list:
    """Validate session ownership and return cached matches with filters applied."""
    if not await cache_service.validate_match_session(user_id, session_id):
        raise HTTPException(status_code=404, detail=_MATCH_SESSION_NOT_FOUND)

    all_matches_data = await cache_service.get_all_matches(user_id, session_id)
    if all_matches_data is None:
        raise HTTPException(status_code=404, detail=_MATCH_SESSION_NOT_FOUND)

    return filter_matches(match_results_from_cache(all_matches_data), **filters)


@router.post(
    "/match",
    responses={
        400: {"description": "Bad request"},
        500: {"description": "Matching query failed"},
        503: {"description": "Service unavailable"},
    },
)
@limiter.limit(RATE_LIMITS["match"])
async def match_resume(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    file: Annotated[UploadFile, File()],
    db: Annotated[AsyncSession, Depends(get_db)],
    cache_service: Annotated[MatchCacheService, Depends(get_match_cache_service)],
    min_score: float = 0.5,
    page_size: int = 20,
) -> MatchResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    try:
        file_content = await read_resume_upload(file)
    except ResumeProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        extracted_text = await extract_resume_text(file.filename, file_content)
    except ResumeProcessingError as exc:
        logger.info("Resume match upload rejected for user %s: %s", current_user.id, exc)
        raise HTTPException(status_code=400, detail=resume_processing_client_message(exc)) from exc

    resume_text = normalize_resume_text(extracted_text)
    if not resume_text:
        raise HTTPException(status_code=400, detail="Resume text is empty after normalization")

    min_score, page_size = _clamp_match_params(min_score, page_size)

    file_hash = hashlib.sha256(file_content).hexdigest()
    cached_response = await return_cached_first_page(
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

    return await build_match_response(
        db=db,
        cache_service=cache_service,
        user_id=current_user.id,
        cache_hash=file_hash,
        min_score=min_score,
        page_size=page_size,
        resume_text=resume_text,
        resume_embedding=resume_embedding,
    )


async def _load_profile_resume(db: AsyncSession, user_id: UUID) -> UserResume:
    try:
        resume_result = await db.execute(select(UserResume).where(UserResume.user_id == user_id))
    except ProgrammingError as exc:
        if is_resume_schema_error(exc):
            raise HTTPException(status_code=503, detail=RESUME_SCHEMA_ERROR_DETAIL) from exc
        raise
    user_resume = resume_result.scalar_one_or_none()
    if user_resume is None:
        raise HTTPException(status_code=400, detail="No profile resume found. Upload one in your profile first.")

    if not user_resume.content_hash:
        raise HTTPException(status_code=400, detail="Stored resume is incomplete. Please upload again.")
    return user_resume


def _profile_resume_needs_reembed(user_resume: UserResume) -> bool:
    settings = get_settings()
    if user_resume.embedding_model != settings.embedding_model:
        return True
    if user_resume.embedding_dim and user_resume.embedding_dim != settings.embedding_dimensions:
        return True
    return user_resume.resume_embedding is None


async def _record_resume_failure(db: AsyncSession, user_resume: UserResume, operation: str, error: str) -> None:
    user_resume.status = "error"
    user_resume.embedding_error = error
    await commit_or_500(
        db,
        operation=operation,
        detail="Failed to update resume status",
        error_mapper=map_resume_schema_commit_error,
    )


async def _reembed_profile_resume(db: AsyncSession, user_resume: UserResume, user_id: UUID) -> tuple[str, list[float]]:
    if not user_resume.encrypted_resume_text:
        raise HTTPException(
            status_code=400,
            detail="Stored resume cannot be re-embedded. Please upload your resume again.",
        )
    try:
        resume_text = decrypt_resume_text(user_resume.encrypted_resume_text)
    except ResumeProcessingError as exc:
        logger.exception("Failed to decrypt stored resume for user %s", user_id)
        await _record_resume_failure(db, user_resume, "record resume decrypt failure", "Failed to decrypt stored resume")
        raise HTTPException(
            status_code=500,
            detail="Failed to decrypt stored resume. Please upload again.",
        ) from exc

    try:
        embedder = QueryEmbeddingService()
        resume_embedding = await embedder.embed(resume_text)
    except Exception as exc:  # noqa: BLE001  # embedding provider failures are surfaced as 503 to the client
        logger.exception("Failed to generate embedding for stored resume")
        await _record_resume_failure(db, user_resume, "record resume embedding failure", "Embedding service unavailable")
        raise HTTPException(
            status_code=503,
            detail="Embedding service unavailable. Please try again later.",
        ) from exc

    user_resume.resume_embedding = resume_embedding
    user_resume.embedding_model = get_settings().embedding_model
    user_resume.embedding_dim = len(resume_embedding)
    user_resume.last_embedded_at = datetime.now(timezone.utc)
    user_resume.status = "ready"
    user_resume.embedding_error = None
    await commit_or_500(db, operation="store re-embedded resume")
    return resume_text, resume_embedding


def _stored_profile_embedding(user_resume: UserResume) -> tuple[str, list[float]]:
    if user_resume.resume_embedding is None:
        raise HTTPException(
            status_code=400,
            detail="Stored resume has no embedding. Please upload your resume again.",
        )
    resume_embedding = list(user_resume.resume_embedding)
    resume_text = decrypt_resume_text(user_resume.encrypted_resume_text) if user_resume.encrypted_resume_text else ""
    return resume_text, resume_embedding


@router.post("/match/profile", responses={400: {"description": "Bad request"}, 500: {"description": "Internal server error"}, 503: {"description": "Service unavailable"}})
@limiter.limit(RATE_LIMITS["match"])
async def match_profile_resume(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    cache_service: Annotated[MatchCacheService, Depends(get_match_cache_service)],
    min_score: float = 0.5,
    page_size: int = 20,
) -> MatchResponse:
    min_score, page_size = _clamp_match_params(min_score, page_size)

    user_resume = await _load_profile_resume(db, current_user.id)
    cache_hash = user_resume.content_hash
    if not cache_hash:
        raise HTTPException(status_code=400, detail="Stored resume is incomplete. Please upload again.")

    cached_response = await return_cached_first_page(
        cache_service=cache_service,
        user_id=current_user.id,
        cache_hash=cache_hash,
        min_score=min_score,
        page_size=page_size,
    )
    if cached_response:
        return cached_response

    if _profile_resume_needs_reembed(user_resume):
        resume_text, resume_embedding = await _reembed_profile_resume(db, user_resume, current_user.id)
    else:
        resume_text, resume_embedding = _stored_profile_embedding(user_resume)

    if not resume_text:
        raise HTTPException(
            status_code=400,
            detail="Stored resume text is unavailable. Please upload your resume again.",
        )

    return await build_match_response(
        db=db,
        cache_service=cache_service,
        user_id=current_user.id,
        cache_hash=cache_hash,
        min_score=min_score,
        page_size=page_size,
        resume_text=resume_text,
        resume_embedding=resume_embedding,
    )


@router.get(
    "/match/{session_id}",
    responses={404: {"description": "Not found"}, 500: {"description": "Matching query failed"}},
)
@limiter.limit(RATE_LIMITS["match"])
async def get_match_page(
    request: Request,
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    cache_service: Annotated[MatchCacheService, Depends(get_match_cache_service)],
    page: Annotated[int, Query(ge=1, description='Page number')] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description='Items per page')] = 20,
    search: Annotated[str | None, Query(description='Search in title, company, description')] = None,
    company: Annotated[str | None, Query(description='Filter by company name')] = None,
    location: Annotated[str | None, Query(description='Filter by location')] = None,
    category: Annotated[str | None, Query(description='Filter by job category')] = None,
    job_type: Annotated[str | None, Query(description='Filter by job type')] = None,
    work_mode: Annotated[str | None, Query(description='Filter by work mode')] = None,
    posted_within: Annotated[str | None, Query(description='Filter by posting date (24h, 7d, 30d)')] = None,
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
    if (page - 1) * page_size > MAX_PAGINATION_OFFSET:
        raise HTTPException(status_code=422, detail=f"pagination offset must not exceed {MAX_PAGINATION_OFFSET}")

    filtered_matches = await _filtered_session_matches(
        cache_service,
        current_user.id,
        session_id,
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
        matches=match_summaries(paginated_matches),
        total=total_count,
        session_id=session_id,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        reused_from_cache=False,
    )


@router.get("/match/{session_id}/facets", response_model=MatchFacetsResponse)
@limiter.limit(RATE_LIMITS["match"])
async def get_match_facets(
    request: Request,
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    cache_service: Annotated[MatchCacheService, Depends(get_match_cache_service)],
    search: Annotated[str | None, Query(description='Search in title, company, description')] = None,
    company: Annotated[str | None, Query(description='Filter by company name')] = None,
    location: Annotated[str | None, Query(description='Filter by location')] = None,
    category: Annotated[str | None, Query(description='Filter by job category')] = None,
    job_type: Annotated[str | None, Query(description='Filter by job type')] = None,
    work_mode: Annotated[str | None, Query(description='Filter by work mode')] = None,
    posted_within: Annotated[str | None, Query(description='Filter by posting date (24h, 7d, 30d)')] = None,
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
    filtered_matches = await _filtered_session_matches(
        cache_service,
        current_user.id,
        session_id,
        search=search,
        company=company,
        location=location,
        category=category,
        job_type=job_type,
        work_mode=work_mode,
        posted_within=posted_within,
    )

    # Calculate facets from filtered matches
    return calculate_facets(filtered_matches)
