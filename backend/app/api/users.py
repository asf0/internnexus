from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.jwt import (
    get_password_hash,
    verify_password,
    validate_password_strength,
)
from app.db import get_db
from app.models import Account, PasswordHistory, User

router = APIRouter(prefix="/users", tags=["users"])


def _parse_user_profile(user: User) -> dict:
    """Helper to parse JSON fields and construct profile dict."""
    skills = json.loads(user.skills) if user.skills else []
    preferred_locations = json.loads(user.preferred_locations) if user.preferred_locations else []
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "image": user.image,
        "created_at": user.created_at,
        "bio": user.bio,
        "phone": user.phone,
        "location": user.location,
        "job_title": user.job_title,
        "company": user.company,
        "industry": user.industry,
        "skills": skills,
        "linkedin_url": user.linkedin_url,
        "portfolio_url": user.portfolio_url,
        "preferred_locations": preferred_locations,
        "has_password": user.hashed_password is not None,
    }


class UserProfileResponse(BaseModel):
    id: str
    email: str
    name: str | None
    image: str | None
    created_at: datetime

    # Profile
    bio: str | None
    phone: str | None
    location: str | None

    # Professional
    job_title: str | None
    company: str | None
    industry: str | None
    skills: list[str]
    linkedin_url: str | None
    portfolio_url: str | None
    preferred_locations: list[str]

    # Auth status
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
def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserProfileResponse:
    """Get the current user's profile."""
    # Parse JSON fields
    return UserProfileResponse(**_parse_user_profile(current_user))


@router.put("/me", response_model=UserProfileResponse)
async def update_user_profile(
    request: Request,
    data: UpdateUserRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    """Update the current user's profile."""
    # Update fields
    if data.name is not None:
        current_user.name = data.name
    if data.bio is not None:
        current_user.bio = data.bio
    if data.phone is not None:
        current_user.phone = data.phone
    if data.location is not None:
        current_user.location = data.location
    if data.job_title is not None:
        current_user.job_title = data.job_title
    if data.company is not None:
        current_user.company = data.company
    if data.industry is not None:
        current_user.industry = data.industry
    if data.linkedin_url is not None:
        current_user.linkedin_url = data.linkedin_url
    if data.portfolio_url is not None:
        current_user.portfolio_url = data.portfolio_url

    # Store JSON fields
    current_user.skills = json.dumps(data.skills) if data.skills else None
    current_user.preferred_locations = (
        json.dumps(data.preferred_locations) if data.preferred_locations else None
    )

    await db.commit()
    await db.refresh(current_user)

    # Return updated profile
    return UserProfileResponse(**_parse_user_profile(current_user))


@router.put("/me/password")
async def change_password(
    request: Request,
    data: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Change or set the user's password."""
    # If user already has a password, verify current password
    if current_user.hashed_password:
        if not data.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Current password is required"},
            )
        if not verify_password(data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Current password is incorrect"},
            )

    # Check if new password is same as current password
    if current_user.hashed_password and verify_password(
        data.new_password, current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "New password cannot be the same as the current password"},
        )

    # Check password history (last 3 passwords)
    history_stmt = (
        select(PasswordHistory)
        .where(PasswordHistory.user_id == current_user.id)
        .order_by(PasswordHistory.created_at.desc())
        .limit(3)
    )
    history_result = await db.execute(history_stmt)
    password_history = history_result.scalars().all()

    for history_entry in password_history:
        if verify_password(data.new_password, history_entry.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Cannot reuse a previous password. Please choose a different password."
                },
            )

    # Store current password in history before changing (if exists)
    if current_user.hashed_password:
        history_entry = PasswordHistory(
            user_id=current_user.id,
            hashed_password=current_user.hashed_password,
        )
        db.add(history_entry)

        # Keep only last 3 passwords in history
        old_history_stmt = (
            select(PasswordHistory)
            .where(PasswordHistory.user_id == current_user.id)
            .order_by(PasswordHistory.created_at.desc())
            .offset(3)
        )
        old_history_result = await db.execute(old_history_stmt)
        old_history = old_history_result.scalars().all()
        for old_entry in old_history:
            await db.delete(old_entry)

    # Hash and set new password
    current_user.hashed_password = get_password_hash(data.new_password)

    # Create credentials account if it doesn't exist
    account_stmt = select(Account).where(
        Account.user_id == current_user.id, Account.provider == "credentials"
    )
    account_result = await db.execute(account_stmt)
    credentials_account = account_result.scalar_one_or_none()

    if not credentials_account:
        account = Account(
            user_id=current_user.id,
            provider="credentials",
            provider_account_id=current_user.email,
        )
        db.add(account)

    await db.commit()

    return {"message": "Password updated successfully"}


@router.delete("/me")
async def delete_account(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Soft delete the current user's account (GDPR compliant)."""
    # Soft delete: mark as deleted and anonymize
    current_user.is_deleted = True
    current_user.deleted_at = datetime.now(timezone.utc)

    # Anonymize personal data
    current_user.name = None
    current_user.email = f"deleted_{current_user.id}@deleted.com"
    current_user.phone = None
    current_user.location = None
    current_user.bio = None
    current_user.image = None
    current_user.job_title = None
    current_user.company = None
    current_user.industry = None
    current_user.linkedin_url = None
    current_user.portfolio_url = None

    # Clear sensitive data
    current_user.hashed_password = None

    # Delete all accounts
    from sqlalchemy import delete

    await db.execute(delete(Account).where(Account.user_id == current_user.id))

    await db.commit()

    return {"message": "Account deleted successfully"}
