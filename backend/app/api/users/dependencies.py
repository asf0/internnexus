"""Shared FastAPI dependencies for the /users routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, security
from app.infra.db import get_db
from app.models import User
from app.services.users.auth_service import AuthService, get_auth_service
from app.services.users.user import UserService, get_user_service


async def current_user_dependency(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    return await get_current_user(credentials, db)


def user_service_dependency(db: AsyncSession = Depends(get_db)) -> UserService:
    return get_user_service(db)


def auth_service_dependency(db: AsyncSession = Depends(get_db)) -> AuthService:
    return get_auth_service(db)
