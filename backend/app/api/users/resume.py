"""Profile resume upload, metadata and deletion."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users.dependencies import current_user_dependency
from app.infra.db import get_db
from app.models import User, UserNotification, UserResume
from app.infra.rate_limiter import RATE_LIMITS, limiter
from app.schemas.users import UserResumeResponse
from app.services.matching.cache import MatchCacheService, get_match_cache_service
from app.services.users.query_embedding import QueryEmbeddingService
from app.services.users.resume import (
    RESUME_SCHEMA_ERROR_DETAIL,
    ResumeProcessingError,
    compute_hash,
    encrypt_resume_text,
    extract_resume_text,
    is_resume_schema_error,
    map_resume_schema_commit_error,
    normalize_resume_text,
    read_resume_upload,
    resume_processing_client_message,
)
from app.infra.commit import commit_or_500, rollback_or_500

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/me/resume", response_model=UserResumeResponse | None)
@limiter.limit(RATE_LIMITS["user_me"])
async def get_resume_metadata(
    request: Request,
    current_user: Annotated[User, Depends(current_user_dependency)],
    db: AsyncSession = Depends(get_db),
) -> UserResumeResponse | None:
    try:
        result = await db.execute(select(UserResume).where(UserResume.user_id == current_user.id))
    except ProgrammingError as exc:
        if is_resume_schema_error(exc):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=RESUME_SCHEMA_ERROR_DETAIL
            ) from exc
        raise
    resume = result.scalar_one_or_none()
    if resume is None:
        return None
    data = UserResumeResponse.model_validate(resume)
    data.has_embedding = resume.resume_embedding is not None
    return data


@router.post("/me/resume", response_model=UserResumeResponse)
@limiter.limit(RATE_LIMITS["user_update"])
async def upload_resume_metadata(
    request: Request,
    current_user: Annotated[User, Depends(current_user_dependency)],
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    cache_service: MatchCacheService = Depends(get_match_cache_service),
) -> UserResumeResponse:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is required")

    filename = file.filename.strip()
    lower = filename.lower()
    if not (lower.endswith(".pdf") or lower.endswith(".txt")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and TXT files are accepted",
        )

    try:
        file_content = await read_resume_upload(file)
    except ResumeProcessingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    file_hash = hashlib.sha256(file_content).hexdigest()

    try:
        resume_text = await extract_resume_text(filename, file_content)
    except ResumeProcessingError as exc:
        logger.info("Resume upload rejected for user %s: %s", current_user.id, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=resume_processing_client_message(exc),
        ) from exc

    normalized_text = normalize_resume_text(resume_text)
    if not normalized_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resume text is empty")

    content_hash = compute_hash(normalized_text)
    encrypted_text = encrypt_resume_text(normalized_text)

    try:
        embedder = QueryEmbeddingService()
        embedding = await embedder.embed(normalized_text)
    except Exception as exc:  # noqa: BLE001  # embedding provider failures are surfaced as 503 to the client
        logger.exception("Failed to generate embedding for uploaded resume")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding service unavailable. Please try again later.",
        ) from exc

    embedding_dim = len(embedding) if embedding else 0
    if embedding_dim == 0:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding service returned an empty vector",
        )

    try:
        existing_result = await db.execute(
            select(UserResume).where(UserResume.user_id == current_user.id)
        )
    except ProgrammingError as exc:
        if is_resume_schema_error(exc):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=RESUME_SCHEMA_ERROR_DETAIL
            ) from exc
        raise
    existing = existing_result.scalar_one_or_none()

    if existing:
        existing.file_name = filename
        existing.file_hash = file_hash
        existing.content_hash = content_hash
        existing.encrypted_resume_text = encrypted_text
        existing.resume_embedding = embedding
        existing.embedding_model = embedder._model
        existing.embedding_dim = embedding_dim
        existing.last_embedded_at = datetime.now(timezone.utc)
        existing.embedding_error = None
        existing.status = "ready"
        db.add(
            UserNotification(
                user_id=current_user.id,
                type="resume.updated",
                payload={"file_name": filename},
            )
        )
        await commit_or_500(
            db,
            operation="update resume metadata",
            detail="Failed to update resume metadata",
            error_mapper=map_resume_schema_commit_error,
        )
        await cache_service.invalidate_user_sessions(current_user.id)
        try:
            await db.refresh(existing)
        except ProgrammingError as exc:
            await rollback_or_500(
                db,
                operation="refresh updated resume metadata",
                detail="Failed to refresh resume metadata",
            )
            if is_resume_schema_error(exc):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=RESUME_SCHEMA_ERROR_DETAIL,
                ) from exc
            raise
        data = UserResumeResponse.model_validate(existing)
        data.has_embedding = existing.resume_embedding is not None
        return data

    resume = UserResume(
        user_id=current_user.id,
        file_name=filename,
        file_hash=file_hash,
        content_hash=content_hash,
        encrypted_resume_text=encrypted_text,
        resume_embedding=embedding,
        embedding_model=embedder._model,
        embedding_dim=embedding_dim,
        last_embedded_at=datetime.now(timezone.utc),
        embedding_error=None,
        status="ready",
    )
    db.add(resume)
    db.add(
        UserNotification(
            user_id=current_user.id,
            type="resume.uploaded",
            payload={"file_name": filename},
        )
    )
    await commit_or_500(
        db,
        operation="create resume metadata",
        detail="Failed to create resume metadata",
        error_mapper=map_resume_schema_commit_error,
    )
    try:
        await db.refresh(resume)
    except ProgrammingError as exc:
        await rollback_or_500(
            db,
            operation="refresh created resume metadata",
            detail="Failed to refresh resume metadata",
        )
        if is_resume_schema_error(exc):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=RESUME_SCHEMA_ERROR_DETAIL
            ) from exc
        raise
    data = UserResumeResponse.model_validate(resume)
    data.has_embedding = resume.resume_embedding is not None
    return data


@router.delete("/me/resume")
@limiter.limit(RATE_LIMITS["user_update"])
async def delete_resume_metadata(
    request: Request,
    current_user: Annotated[User, Depends(current_user_dependency)],
    db: AsyncSession = Depends(get_db),
    cache_service: MatchCacheService = Depends(get_match_cache_service),
) -> dict[str, str]:
    await db.execute(delete(UserResume).where(UserResume.user_id == current_user.id))
    await commit_or_500(db, operation="delete resume metadata")
    await cache_service.invalidate_user_sessions(current_user.id)
    return {"message": "Resume metadata deleted"}
