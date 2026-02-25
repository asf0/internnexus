from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth.jwt import decode_access_token
from app.db import get_db
from app.models import Admin, AdminRole, User

security = HTTPBearer(auto_error=False)


def _validate_password_change(token_payload: dict, user: User) -> bool:
    """Validate that token was issued after last password change.

    Args:
        token_payload: Decoded JWT payload
        user: User object from database

    Returns:
        True if token is valid, False if password was changed after token issuance
    """
    token_pw_changed = token_payload.get("pw_changed")
    user_pw_changed = user.password_changed_at

    if token_pw_changed is None:
        return True

    if user_pw_changed is None:
        return True

    token_timestamp = token_pw_changed
    user_timestamp = user_pw_changed.timestamp()

    return token_timestamp >= user_timestamp


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency to get the current authenticated user from JWT token.

    Args:
        credentials: The Authorization header with Bearer token
        db: Database session

    Returns:
        The authenticated User object

    Raises:
        HTTPException: If authentication fails
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not _validate_password_change(payload, user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalidated by password change. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Dependency to optionally get the current user if authenticated.

    Unlike get_current_user, this doesn't raise an error if not authenticated.
    Useful for endpoints that work for both authenticated and anonymous users.

    Args:
        credentials: The Authorization header with Bearer token
        db: Database session

    Returns:
        The User object if authenticated, None otherwise
    """
    if credentials is None:
        return None

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        return None

    user_id_str = payload.get("sub")
    if user_id_str is None:
        return None

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        return None

    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        return None

    if not _validate_password_change(payload, user):
        return None

    return user


async def get_current_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: AsyncSession = Depends(get_db),
) -> Admin:
    """Dependency to get the current authenticated admin from JWT token.

    First authenticates the user, then verifies they have admin access.

    Args:
        credentials: The Authorization header with Bearer token
        db: Database session

    Returns:
        The Admin object for the authenticated user

    Raises:
        HTTPException: If authentication fails or user is not an admin
    """
    user = await get_current_user(credentials, db)

    result = await db.execute(select(Admin).filter(Admin.user_id == user.id))
    admin = result.scalar_one_or_none()

    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return admin


async def get_current_super_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: AsyncSession = Depends(get_db),
) -> Admin:
    """Dependency to get the current authenticated super admin from JWT token.

    First authenticates the user, then verifies they have super admin access.

    Args:
        credentials: The Authorization header with Bearer token
        db: Database session

    Returns:
        The Admin object for the authenticated super admin

    Raises:
        HTTPException: If authentication fails or user is not a super admin
    """
    admin = await get_current_admin(credentials, db)

    if admin.role != AdminRole.super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )

    return admin


# Type aliases for dependency injection
AdminDep = Annotated[Admin, Depends(get_current_admin)]
SuperAdminDep = Annotated[Admin, Depends(get_current_super_admin)]
