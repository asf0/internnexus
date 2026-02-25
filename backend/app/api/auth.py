"""Authentication API endpoints - refactored to use service layer."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.jwt import validate_password_strength
from app.auth.oauth import OAuthVerificationError, verify_oauth_token
from app.db import get_db
from app.models import User
from app.rate_limiter import RATE_LIMITS, limiter
from app.services.auth_service import AuthService, get_auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        is_valid, error_message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_message)
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class OAuthCallbackRequest(BaseModel):
    provider: str = Field(..., pattern="^(google|github)$")
    provider_account_id: str
    email: EmailStr
    name: str | None = None
    image: str | None = None
    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None


class SetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=8)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


async def _get_auth_service_dependency(db: AsyncSession = Depends(get_db)) -> AuthService:
    return await get_auth_service(db)


@router.post("/register", response_model=AuthResponse)
@limiter.limit(RATE_LIMITS["auth_register"])
async def register(
    request: Request,
    data: RegisterRequest,
    auth_service: AuthService = Depends(_get_auth_service_dependency),
) -> AuthResponse:
    user, access_token = await auth_service.register_user(
        email=data.email,
        password=data.password,
        name=data.name,
    )
    return AuthResponse(
        access_token=access_token,
        user={"id": str(user.id), "email": user.email, "name": user.name},
    )


@router.post("/login", response_model=AuthResponse)
@limiter.limit(RATE_LIMITS["auth_login"])
async def login(
    request: Request,
    data: LoginRequest,
    auth_service: AuthService = Depends(_get_auth_service_dependency),
) -> AuthResponse:
    user, access_token = await auth_service.login_user(
        email=data.email,
        password=data.password,
    )
    return AuthResponse(
        access_token=access_token,
        user={"id": str(user.id), "email": user.email, "name": user.name},
    )


@router.post("/oauth/callback", response_model=AuthResponse)
@limiter.limit(RATE_LIMITS["auth_oauth"])
async def oauth_callback(
    request: Request,
    data: OAuthCallbackRequest,
    auth_service: AuthService = Depends(_get_auth_service_dependency),
) -> AuthResponse:
    try:
        verified_user = await verify_oauth_token(data.provider, data.access_token)
    except OAuthVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "OAUTH_VERIFICATION_FAILED",
                "message": f"Failed to verify {exc.provider} token: {exc.message}",
            },
        )

    user, access_token = await auth_service.handle_oauth_callback(
        provider=data.provider,
        provider_account_id=verified_user.provider_account_id,
        email=verified_user.email,
        name=verified_user.name or data.name,
        picture=verified_user.picture or data.image,
        access_token=data.access_token,
        refresh_token=data.refresh_token,
        expires_at=data.expires_at,
    )

    return AuthResponse(
        access_token=access_token,
        user={"id": str(user.id), "email": user.email, "name": user.name},
    )


@router.post("/set-password", response_model=AuthResponse)
@limiter.limit(RATE_LIMITS["auth_set_password"])
async def set_password(
    request: Request,
    data: SetPasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: AuthService = Depends(_get_auth_service_dependency),
) -> AuthResponse:
    user, access_token = await auth_service.set_password(current_user, data.password)
    return AuthResponse(
        access_token=access_token,
        user={"id": str(user.id), "email": user.email, "name": user.name},
    )
