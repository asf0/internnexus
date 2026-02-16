"""User repository for database operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        """Get a user by email address."""
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_accounts(self, user_id: UUID) -> User | None:
        """Get a user by ID with accounts loaded."""
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        """Check if an email is already registered."""
        stmt = select(User.id).where(User.email == email).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create_user(
        self,
        email: str,
        hashed_password: str | None = None,
        name: str | None = None,
        image: str | None = None,
        email_verified: bool = False,
    ) -> User:
        """Create a new user."""
        return await self.create(
            email=email,
            hashed_password=hashed_password,
            name=name,
            image=image,
            email_verified=email_verified,
        )
