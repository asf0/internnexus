"""In-app notification listing and read/delete state."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users.dependencies import current_user_dependency
from app.infra.db import get_db
from app.models import User, UserNotification
from app.infra.rate_limiter import RATE_LIMITS, limiter
from app.schemas.users import NotificationResponse
from app.infra.commit import commit_or_500

router = APIRouter()


@router.get("/me/notifications", response_model=list[NotificationResponse])
@limiter.limit(RATE_LIMITS["user_me"])
async def list_notifications(
    request: Request,
    current_user: Annotated[User, Depends(current_user_dependency)],
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
    current_user: Annotated[User, Depends(current_user_dependency)],
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
    current_user: Annotated[User, Depends(current_user_dependency)],
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
    await commit_or_500(db, operation="mark notification read")
    return {"message": "Notification marked as read"}


@router.patch("/me/notifications/read-all")
@limiter.limit(RATE_LIMITS["user_update"])
async def mark_all_notifications_read(
    request: Request,
    current_user: Annotated[User, Depends(current_user_dependency)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(
        select(UserNotification).where(UserNotification.user_id == current_user.id)
    )
    rows = result.scalars().all()
    now = datetime.now(timezone.utc)
    for row in rows:
        if not row.is_read:
            row.is_read = True
            row.read_at = now
    await commit_or_500(db, operation="mark all notifications read")
    return {"message": "All notifications marked as read"}


@router.delete("/me/notifications/{notification_id}")
@limiter.limit(RATE_LIMITS["user_update"])
async def delete_notification(
    request: Request,
    notification_id: UUID,
    current_user: Annotated[User, Depends(current_user_dependency)],
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
    await db.delete(row)
    await commit_or_500(db, operation="delete notification")
    return {"message": "Notification deleted"}


@router.delete("/me/notifications")
@limiter.limit(RATE_LIMITS["user_update"])
async def clear_all_notifications(
    request: Request,
    current_user: Annotated[User, Depends(current_user_dependency)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(
        select(UserNotification).where(UserNotification.user_id == current_user.id)
    )
    rows = result.scalars().all()
    for row in rows:
        await db.delete(row)
    await commit_or_500(db, operation="clear all notifications")
    return {"message": "All notifications cleared"}
