"""Saved and applied job tracking for the signed-in user."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users.dependencies import current_user_dependency
from app.infra.db import get_db
from app.models import User
from app.infra.rate_limiter import RATE_LIMITS, limiter
from app.schemas.mappers import job_to_summary
from app.schemas.users import SavedJobResponse
from app.services.users.user_job import JobNotFoundError, UserJobService

router = APIRouter()


@router.get("/me/saved-jobs/ids", response_model=list[UUID])
@limiter.limit(RATE_LIMITS["user_me"])
async def list_saved_job_ids(
    request: Request,
    current_user: Annotated[User, Depends(current_user_dependency)],
    db: AsyncSession = Depends(get_db),
) -> list[UUID]:
    return await UserJobService(db).list_saved_ids(current_user.id)


@router.get("/me/applied-jobs/ids", response_model=list[UUID])
@limiter.limit(RATE_LIMITS["user_me"])
async def list_applied_job_ids(
    request: Request,
    current_user: Annotated[User, Depends(current_user_dependency)],
    db: AsyncSession = Depends(get_db),
) -> list[UUID]:
    return await UserJobService(db).list_applied_ids(current_user.id)


@router.get("/me/saved-jobs", response_model=list[SavedJobResponse])
@limiter.limit(RATE_LIMITS["user_me"])
async def list_saved_jobs(
    request: Request,
    current_user: Annotated[User, Depends(current_user_dependency)],
    db: AsyncSession = Depends(get_db),
) -> list[SavedJobResponse]:
    rows = await UserJobService(db).list_saved(current_user.id)
    return [
        SavedJobResponse(
            id=saved.id, job_id=saved.job_id, created_at=saved.created_at,
            job=job_to_summary(job),
        )
        for saved, job in rows
    ]


@router.post("/me/saved-jobs/{job_id}")
@limiter.limit(RATE_LIMITS["user_update"])
async def save_job(
    request: Request,
    job_id: UUID,
    current_user: Annotated[User, Depends(current_user_dependency)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    try:
        created = await UserJobService(db).save(current_user.id, job_id)
    except JobNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return {"message": "Job saved" if created else "Job already saved"}


@router.delete("/me/saved-jobs/{job_id}")
@limiter.limit(RATE_LIMITS["user_update"])
async def unsave_job(
    request: Request,
    job_id: UUID,
    current_user: Annotated[User, Depends(current_user_dependency)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    removed = await UserJobService(db).unsave(current_user.id, job_id)
    return {"message": "Job unsaved" if removed else "Job was not saved"}


@router.post("/me/applied-jobs/{job_id}")
@limiter.limit(RATE_LIMITS["user_update"])
async def mark_job_applied(
    request: Request,
    job_id: UUID,
    current_user: Annotated[User, Depends(current_user_dependency)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    try:
        created = await UserJobService(db).mark_applied(current_user.id, job_id)
    except JobNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return {"message": "Job marked as applied" if created else "Job already marked as applied"}


@router.delete("/me/applied-jobs/{job_id}")
@limiter.limit(RATE_LIMITS["user_update"])
async def unmark_job_applied(
    request: Request,
    job_id: UUID,
    current_user: Annotated[User, Depends(current_user_dependency)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    removed = await UserJobService(db).unmark_applied(current_user.id, job_id)
    return {"message": "Job unmarked as applied" if removed else "Job was not marked as applied"}
