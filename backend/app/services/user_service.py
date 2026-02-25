"""User service for profile management."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from typing import TypedDict

from fastapi import Depends
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Account, User
from app.repositories.account import AccountRepository
from app.repositories.user import UserRepository


class UserProfileData(TypedDict):
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


class UpdateProfileData(TypedDict, total=False):
    name: str | None
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


def _json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return []


class UserService:
    """Service for user profile management."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.account_repo = AccountRepository(session)

    @staticmethod
    def parse_user_profile(user: User) -> UserProfileData:
        """Parse user model to profile dict with JSON fields decoded."""
        skills = _json_list(user.skills)
        preferred_locations = _json_list(user.preferred_locations)
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

    async def update_profile(self, user: User, data: UpdateProfileData) -> User:
        """Update user profile fields."""
        name = data.get("name")
        if name is not None:
            user.name = name
        bio = data.get("bio")
        if bio is not None:
            user.bio = bio
        phone = data.get("phone")
        if phone is not None:
            user.phone = phone
        location = data.get("location")
        if location is not None:
            user.location = location
        job_title = data.get("job_title")
        if job_title is not None:
            user.job_title = job_title
        company = data.get("company")
        if company is not None:
            user.company = company
        industry = data.get("industry")
        if industry is not None:
            user.industry = industry
        linkedin_url = data.get("linkedin_url")
        if linkedin_url is not None:
            user.linkedin_url = linkedin_url
        portfolio_url = data.get("portfolio_url")
        if portfolio_url is not None:
            user.portfolio_url = portfolio_url

        skills = data.get("skills", [])
        preferred_locations = data.get("preferred_locations", [])
        user.skills = json.dumps(skills) if skills else None
        user.preferred_locations = json.dumps(preferred_locations) if preferred_locations else None

        await self.session.commit()
        await self.user_repo.refresh(user)
        return user

    async def delete_account(self, user: User) -> None:
        """Soft delete user account (GDPR compliant)."""
        user.is_deleted = True
        user.deleted_at = datetime.now(timezone.utc)

        user.name = None
        random_suffix = secrets.token_hex(8)
        user.email = f"deleted_{random_suffix}@deleted.invalid"
        user.phone = None
        user.location = None
        user.bio = None
        user.image = None
        user.job_title = None
        user.company = None
        user.industry = None
        user.linkedin_url = None
        user.portfolio_url = None
        user.hashed_password = None
        user.password_changed_at = None

        await self.session.execute(delete(Account).where(Account.user_id == user.id))
        await self.session.commit()


async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """Dependency to get UserService instance."""
    return UserService(db)
