"""Authentication API endpoints - refactored to use service layer."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AuthenticatedSession, get_authenticated_session, get_current_user
from app.auth.jwt import ensure_password_strength
from app.auth.oauth import OAuthVerificationError, verify_oauth_token
from app.infra.db import get_db
from app.models import User
from app.infra.rate_limiter import RATE_LIMITS, limiter
from app.services.users.auth_service import AuthService, get_auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return ensure_password_strength(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class OAuthCallbackRequest(BaseModel):
    provider: str = Field(..., pattern="^(google|github)$")
    access_token: str

    model_config = ConfigDict(extra="forbid")


class SetPasswordRequest(BaseModel):
    password: str

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return ensure_password_strength(v)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


def _auth_response(user: User, access_token: str) -> AuthResponse:
    """Build the shared auth payload; ``user`` shape is a frontend contract."""
    return AuthResponse(
        access_token=access_token,
        user={"id": str(user.id), "email": user.email, "name": user.name},
    )


def _get_auth_service_dependency(db: AsyncSession = Depends(get_db)) -> AuthService:
    return get_auth_service(db)


@router.post("/register")
@limiter.limit(RATE_LIMITS["auth_register"])
async def register(
    request: Request,
    data: RegisterRequest,
    auth_service: Annotated[AuthService, Depends(_get_auth_service_dependency)],
) -> AuthResponse:
    user, access_token = await auth_service.register_user(
        email=data.email,
        password=data.password,
        name=data.name,
    )
    return _auth_response(user, access_token)


@router.post("/login")
@limiter.limit(RATE_LIMITS["auth_login"])
async def login(
    request: Request,
    data: LoginRequest,
    auth_service: Annotated[AuthService, Depends(_get_auth_service_dependency)],
) -> AuthResponse:
    user, access_token = await auth_service.login_user(
        email=data.email,
        password=data.password,
    )
    return _auth_response(user, access_token)


@router.post("/oauth/callback", responses={401: {"description": "Unauthorized"}})
@limiter.limit(RATE_LIMITS["auth_oauth"])
async def oauth_callback(
    request: Request,
    data: OAuthCallbackRequest,
    auth_service: Annotated[AuthService, Depends(_get_auth_service_dependency)],
) -> AuthResponse:
    try:
        verified_user = await verify_oauth_token(data.provider, data.access_token)
    except OAuthVerificationError as exc:
        # Log the provider and underlying reason server-side; return a generic
        # message so infrastructure/provider details are not leaked to clients.
        logger.warning("OAuth verification failed for provider %s: %s", exc.provider, exc.message)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "OAUTH_VERIFICATION_FAILED",
                "message": "OAuth verification failed.",
            },
        ) from exc

    user, access_token = await auth_service.handle_oauth_callback(
        provider=data.provider,
        provider_account_id=verified_user.provider_account_id,
        email=verified_user.email,
        name=verified_user.name,
        picture=verified_user.picture,
    )

    return _auth_response(user, access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    authenticated: Annotated[AuthenticatedSession, Depends(get_authenticated_session)],
    auth_service: Annotated[AuthService, Depends(_get_auth_service_dependency)],
) -> Response:
    """Revoke the database session backing the current bearer token."""
    await auth_service.logout(authenticated.session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/set-password")
@limiter.limit(RATE_LIMITS["auth_set_credential"])
async def set_password(
    request: Request,
    data: SetPasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(_get_auth_service_dependency)],
) -> AuthResponse:
    user, access_token = await auth_service.set_password(current_user, data.password)
    return _auth_response(user, access_token)
