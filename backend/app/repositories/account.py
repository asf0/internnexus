"""Account repository for database operations."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, PasswordHistory
from app.repositories.base import BaseRepository


class AccountRepository(BaseRepository[Account]):
    """Repository for Account model operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Account, session)

    async def get_by_provider(
        self,
        user_id: UUID,
        provider: str,
        provider_account_id: str,
    ) -> Account | None:
        """Get an account by provider and provider account ID."""
        stmt = select(Account).where(
            Account.user_id == user_id,
            Account.provider == provider,
            Account.provider_account_id == provider_account_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_oauth_accounts(self, user_id: UUID) -> list[Account]:
        """Get all OAuth accounts for a user."""
        stmt = select(Account).where(
            Account.user_id == user_id,
            Account.provider.in_(["google", "github"]),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_oauth_providers(self, user_id: UUID) -> list[str]:
        """Get list of OAuth provider names for a user."""
        stmt = select(Account.provider).where(
            Account.user_id == user_id,
            Account.provider.in_(["google", "github"]),
        )
        result = await self.session.execute(stmt)
        return [p.capitalize() for p in result.scalars().all()]

    async def get_credentials_account(self, user_id: UUID) -> Account | None:
        """Get the credentials account for a user."""
        stmt = select(Account).where(
            Account.user_id == user_id,
            Account.provider == "credentials",
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_oauth_account(
        self,
        user_id: UUID,
        provider: str,
        provider_account_id: str,
        access_token: str | None = None,
        refresh_token: str | None = None,
        expires_at: datetime | None = None,
    ) -> Account:
        """Create a new OAuth account."""
        return await self.create(
            user_id=user_id,
            provider=provider,
            provider_account_id=provider_account_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )

    async def create_credentials_account(self, user_id: UUID, email: str) -> Account:
        """Create a new credentials account."""
        return await self.create(
            user_id=user_id,
            provider="credentials",
            provider_account_id=email,
        )


class PasswordHistoryRepository(BaseRepository[PasswordHistory]):
    """Repository for PasswordHistory model operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(PasswordHistory, session)

    async def get_recent_passwords(self, user_id: UUID, limit: int = 3) -> list[PasswordHistory]:
        """Get recent password history for a user."""
        stmt = (
            select(PasswordHistory)
            .where(PasswordHistory.user_id == user_id)
            .order_by(PasswordHistory.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_password_history(self, user_id: UUID, hashed_password: str) -> PasswordHistory:
        """Add a password to history."""
        return await self.create(
            user_id=user_id,
            hashed_password=hashed_password,
        )

    async def delete_old_password_history(self, user_id: UUID, keep: int = 3) -> int:
        """Delete old password history entries, keeping the most recent ones."""
        stmt = (
            select(PasswordHistory.id)
            .where(PasswordHistory.user_id == user_id)
            .order_by(PasswordHistory.created_at.desc())
            .offset(keep)
        )
        result = await self.session.execute(stmt)
        ids_to_delete = [row[0] for row in result.all()]

        if ids_to_delete:
            from sqlalchemy import delete

            delete_stmt = delete(PasswordHistory).where(PasswordHistory.id.in_(ids_to_delete))
            await self.session.execute(delete_stmt)
            return len(ids_to_delete)
        return 0
