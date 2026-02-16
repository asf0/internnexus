"""User API endpoints - refactored to use service layer."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.auth.dependencies import get_current_user
from app.auth.jwt import validate_password_strength
from app.models import User
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
