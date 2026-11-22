"""Single-request homepage state for the signed-in user."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users.dependencies import current_user_dependency
from app.infra.db import get_db
from app.infra.rate_limiter import RATE_LIMITS, limiter
from app.models import User
from app.schemas.users import HomeStateResponse
from app.services.users.home_state import HomeStateService

router = APIRouter()


@router.get("/me/home-state", response_model=HomeStateResponse)
@limiter.limit(RATE_LIMITS["user_me"])
async def get_home_state(
    request: Request,
    current_user: Annotated[User, Depends(current_user_dependency)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HomeStateResponse:
    """Return unread count, saved ids, and applied ids in one round trip."""
    return await HomeStateService(db).get(current_user.id)
