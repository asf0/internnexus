"""Profile read/update, password change and account deletion."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request

from app.api.users.dependencies import (
    auth_service_dependency,
    current_user_dependency,
    user_service_dependency,
)
from app.models import User
from app.infra.rate_limiter import RATE_LIMITS, limiter
from app.schemas.users import ChangePasswordRequest, UpdateUserRequest, UserProfileResponse
from app.services.users.auth_service import AuthService
from app.services.users.user import UpdateProfileData, UserService

router = APIRouter()


@router.get("/me", response_model=UserProfileResponse)
@limiter.limit(RATE_LIMITS["user_me"])
def get_current_user_profile(
    request: Request,
    current_user: Annotated[User, Depends(current_user_dependency)],
    user_service: UserService = Depends(user_service_dependency),
) -> UserProfileResponse:
    return UserProfileResponse(**user_service.parse_user_profile(current_user))


@router.put("/me", response_model=UserProfileResponse)
@limiter.limit(RATE_LIMITS["user_update"])
async def update_user_profile(
    request: Request,
    data: UpdateUserRequest,
    current_user: Annotated[User, Depends(current_user_dependency)],
    user_service: UserService = Depends(user_service_dependency),
) -> UserProfileResponse:
    profile_update = cast(UpdateProfileData, data.model_dump())
    user = await user_service.update_profile(current_user, profile_update)
    return UserProfileResponse(**user_service.parse_user_profile(user))


@router.put("/me/password")
@limiter.limit(RATE_LIMITS["auth_set_credential"])
async def change_password(
    request: Request,
    data: ChangePasswordRequest,
    current_user: Annotated[User, Depends(current_user_dependency)],
    auth_service: AuthService = Depends(auth_service_dependency),
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
    current_user: Annotated[User, Depends(current_user_dependency)],
    user_service: UserService = Depends(user_service_dependency),
) -> dict:
    await user_service.delete_account(current_user)
    return {"message": "Account deleted successfully"}
