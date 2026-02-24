"""User API endpoints - refactored to use service layer."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.jwt import validate_password_strength
from app.db import get_db
from app.api.schemas import JobResponse
from app.models import AppliedJob, Job, SavedJob, User, UserNotification, UserResume
from app.rate_limiter import RATE_LIMITS, limiter
from app.services.auth_service import AuthService, get_auth_service
from app.services.user_service import UserService, get_user_service

router = APIRouter(prefix="/users", tags=["users"])


class UserProfileResponse(BaseModel):
    id: str
    email: str
    name: str | None
    image: str | None
    created_at: datetime
    bio: str | None
    phone: str | None
    location: str | None
    job_title: str | None
    company: str | None
    industry: str | None
    skills: list[str]
    linkedin_url: str | None
    portfolio_url: str | None
    preferred_locations: list[str]
    has_password: bool

    model_config = ConfigDict(from_attributes=True)


class UpdateUserRequest(BaseModel):
    name: str | None = None
    bio: str | None = None
    phone: str | None = None
    location: str | None = None
    job_title: str | None = None
    company: str | None = None
    industry: str | None = None
    skills: list[str] = Field(default_factory=list)
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    preferred_locations: list[str] = Field(default_factory=list)


class ChangePasswordRequest(BaseModel):
    current_password: str | None = None
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        is_valid, error_message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_message)
        return v


class UserResumeResponse(BaseModel):
    id: UUID
    file_name: str
    file_hash: str
    status: str
    uploaded_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationResponse(BaseModel):
    id: UUID
    type: str
    payload: dict[str, Any]
    is_read: bool
    created_at: datetime
    read_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class SavedJobResponse(BaseModel):
    id: UUID
    job_id: UUID
    created_at: datetime
    job: JobResponse

    model_config = ConfigDict(from_attributes=True)


@router.get("/me", response_model=UserProfileResponse)
@limiter.limit(RATE_LIMITS["user_me"])
def get_current_user_profile(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: UserService = Depends(get_user_service),
) -> UserProfileResponse:
    return UserProfileResponse(**user_service.parse_user_profile(current_user))


@router.put("/me", response_model=UserProfileResponse)
@limiter.limit(RATE_LIMITS["user_update"])
async def update_user_profile(
    request: Request,
    data: UpdateUserRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: UserService = Depends(get_user_service),
) -> UserProfileResponse:
    user = await user_service.update_profile(current_user, data.model_dump())
    return UserProfileResponse(**user_service.parse_user_profile(user))


@router.put("/me/password")
@limiter.limit(RATE_LIMITS["auth_set_password"])
async def change_password(
    request: Request,
    data: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: AuthService = Depends(get_auth_service),
) -> dict:
    await auth_service.change_password(
        user=current_user,
        current_password=data.current_password,
        new_password=data.new_password,
    )
    return {"message": "Password updated successfully"}


@router.delete("/me")
@limiter.limit(RATE_LIMITS["user_delete"])
async def delete_account(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: UserService = Depends(get_user_service),
) -> dict:
    await user_service.delete_account(current_user)
    return {"message": "Account deleted successfully"}


@router.get("/me/resume", response_model=UserResumeResponse | None)
@limiter.limit(RATE_LIMITS["user_me"])
async def get_resume_metadata(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> UserResumeResponse | None:
    result = await db.execute(select(UserResume).where(UserResume.user_id == current_user.id))
    resume = result.scalar_one_or_none()
    if resume is None:
        return None
    return UserResumeResponse.model_validate(resume)


@router.post("/me/resume", response_model=UserResumeResponse)
@limiter.limit(RATE_LIMITS["user_update"])
async def upload_resume_metadata(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
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

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File too large (max 10MB)")

    file_hash = hashlib.sha256(content).hexdigest()

    existing_result = await db.execute(select(UserResume).where(UserResume.user_id == current_user.id))
    existing = existing_result.scalar_one_or_none()

    if existing:
        existing.file_name = filename
        existing.file_hash = file_hash
        existing.status = "ready"
        db.add(
            UserNotification(
                user_id=current_user.id,
                type="resume.updated",
                payload={"file_name": filename},
            )
        )
        await db.commit()
        await db.refresh(existing)
        return UserResumeResponse.model_validate(existing)

    resume = UserResume(
        user_id=current_user.id,
        file_name=filename,
        file_hash=file_hash,
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
    await db.commit()
    await db.refresh(resume)
    return UserResumeResponse.model_validate(resume)


@router.delete("/me/resume")
@limiter.limit(RATE_LIMITS["user_update"])
async def delete_resume_metadata(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    await db.execute(delete(UserResume).where(UserResume.user_id == current_user.id))
    await db.commit()
    return {"message": "Resume metadata deleted"}


@router.get("/me/notifications", response_model=list[NotificationResponse])
@limiter.limit(RATE_LIMITS["user_me"])
async def list_notifications(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
) -> list[NotificationResponse]:
    safe_limit = max(1, min(limit, 200))
    result = await db.execute(
        select(UserNotification)
        .where(UserNotification.user_id == current_user.id)
        .order_by(UserNotification.created_at.desc())
        .limit(safe_limit)
    )
    rows = result.scalars().all()
    return [NotificationResponse.model_validate(row) for row in rows]


@router.get("/me/notifications/unread-count")
@limiter.limit(RATE_LIMITS["user_me"])
async def get_unread_notifications_count(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    result = await db.execute(
        select(func.count(UserNotification.id)).where(
            UserNotification.user_id == current_user.id,
            UserNotification.is_read.is_(False),
        )
    )
    return {"unread_count": int(result.scalar() or 0)}


@router.patch("/me/notifications/{notification_id}/read")
@limiter.limit(RATE_LIMITS["user_update"])
async def mark_notification_read(
    request: Request,
    notification_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(
        select(UserNotification).where(
            UserNotification.id == notification_id,
            UserNotification.user_id == current_user.id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    row.is_read = True
    row.read_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Notification marked as read"}


@router.patch("/me/notifications/read-all")
@limiter.limit(RATE_LIMITS["user_update"])
async def mark_all_notifications_read(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(select(UserNotification).where(UserNotification.user_id == current_user.id))
    rows = result.scalars().all()
    now = datetime.now(timezone.utc)
    for row in rows:
        if not row.is_read:
            row.is_read = True
            row.read_at = now
    await db.commit()
    return {"message": "All notifications marked as read"}


@router.get("/me/saved-jobs/ids", response_model=list[UUID])
@limiter.limit(RATE_LIMITS["user_me"])
async def list_saved_job_ids(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[UUID]:
    result = await db.execute(
        select(SavedJob.job_id)
        .where(SavedJob.user_id == current_user.id)
        .order_by(SavedJob.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/me/applied-jobs/ids", response_model=list[UUID])
@limiter.limit(RATE_LIMITS["user_me"])
async def list_applied_job_ids(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[UUID]:
    result = await db.execute(
        select(AppliedJob.job_id)
        .where(AppliedJob.user_id == current_user.id)
        .order_by(AppliedJob.applied_at.desc())
    )
    return list(result.scalars().all())


@router.get("/me/saved-jobs", response_model=list[SavedJobResponse])
@limiter.limit(RATE_LIMITS["user_me"])
async def list_saved_jobs(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[SavedJobResponse]:
    result = await db.execute(
        select(SavedJob, Job)
        .join(Job, SavedJob.job_id == Job.id)
        .where(SavedJob.user_id == current_user.id)
        .order_by(SavedJob.created_at.desc())
    )
    rows = result.all()
    return [
        SavedJobResponse(
            id=row.SavedJob.id,
            job_id=row.SavedJob.job_id,
            created_at=row.SavedJob.created_at,
            job=JobResponse.model_validate(row.Job),
        )
        for row in rows
    ]


@router.post("/me/saved-jobs/{job_id}")
@limiter.limit(RATE_LIMITS["user_update"])
async def save_job(
    request: Request,
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    job_result = await db.execute(select(Job).where(Job.id == job_id, Job.is_active.is_(True)))
    job = job_result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    existing_result = await db.execute(
        select(SavedJob).where(SavedJob.user_id == current_user.id, SavedJob.job_id == job_id)
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        return {"message": "Job already saved"}

    db.add(SavedJob(user_id=current_user.id, job_id=job_id))
    await db.commit()
    return {"message": "Job saved"}


@router.delete("/me/saved-jobs/{job_id}")
@limiter.limit(RATE_LIMITS["user_update"])
async def unsave_job(
    request: Request,
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(
        select(SavedJob).where(SavedJob.user_id == current_user.id, SavedJob.job_id == job_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return {"message": "Job was not saved"}
    await db.delete(row)
    await db.commit()
    return {"message": "Job unsaved"}


@router.post("/me/applied-jobs/{job_id}")
@limiter.limit(RATE_LIMITS["user_update"])
async def mark_job_applied(
    request: Request,
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    job_result = await db.execute(select(Job).where(Job.id == job_id, Job.is_active.is_(True)))
    job = job_result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    existing_result = await db.execute(
        select(AppliedJob).where(AppliedJob.user_id == current_user.id, AppliedJob.job_id == job_id)
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        return {"message": "Job already marked as applied"}

    db.add(AppliedJob(user_id=current_user.id, job_id=job_id))
    await db.commit()
    return {"message": "Job marked as applied"}


@router.delete("/me/applied-jobs/{job_id}")
@limiter.limit(RATE_LIMITS["user_update"])
async def unmark_job_applied(
    request: Request,
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(
        select(AppliedJob).where(AppliedJob.user_id == current_user.id, AppliedJob.job_id == job_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return {"message": "Job was not marked as applied"}
    await db.delete(row)
    await db.commit()
    return {"message": "Job unmarked as applied"}
