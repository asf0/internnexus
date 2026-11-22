from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MCPApiKey, User

MCP_KEY_PREFIX = "inx_mcp_"
DEFAULT_EXPIRY_DAYS = 90
MAX_EXPIRY_DAYS = 365


@dataclass(frozen=True)
class CreatedMCPApiKey:
    record: MCPApiKey
    secret: str


@dataclass(frozen=True)
class AuthenticatedMCPPrincipal:
    user: User
    key_id: UUID


class MCPApiKeyService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def hash_secret(secret: str) -> str:
        return hashlib.sha256(secret.encode("utf-8")).hexdigest()

    async def create(self, user_id: UUID, name: str, expires_in_days: int = DEFAULT_EXPIRY_DAYS) -> CreatedMCPApiKey:
        days = min(max(expires_in_days, 1), MAX_EXPIRY_DAYS)
        secret = MCP_KEY_PREFIX + secrets.token_urlsafe(32)
        record = MCPApiKey(
            user_id=user_id,
            name=name.strip(),
            key_hash=self.hash_secret(secret),
            key_prefix=secret[:20],
            expires_at=datetime.now(timezone.utc) + timedelta(days=days),
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return CreatedMCPApiKey(record=record, secret=secret)

    async def list_for_user(self, user_id: UUID) -> list[MCPApiKey]:
        result = await self.session.execute(
            select(MCPApiKey)
            .where(MCPApiKey.user_id == user_id, MCPApiKey.revoked_at.is_(None))
            .order_by(MCPApiKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke(self, user_id: UUID, key_id: UUID) -> bool:
        result = await self.session.execute(
            select(MCPApiKey).where(MCPApiKey.id == key_id, MCPApiKey.user_id == user_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return False
        if record.revoked_at is None:
            record.revoked_at = datetime.now(timezone.utc)
            await self.session.commit()
        return True

    async def authenticate(self, secret: str) -> User | None:
        principal = await self.authenticate_principal(secret)
        return principal.user if principal else None

    async def authenticate_principal(self, secret: str) -> AuthenticatedMCPPrincipal | None:
        """Authenticate a key while retaining its durable identifier for analytics."""
        if not secret.startswith(MCP_KEY_PREFIX):
            return None
        result = await self.session.execute(
            select(MCPApiKey, User)
            .join(User, User.id == MCPApiKey.user_id)
            .where(MCPApiKey.key_hash == self.hash_secret(secret))
        )
        row = result.one_or_none()
        if row is None:
            return None
        record, user = row
        now = datetime.now(timezone.utc)
        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if record.revoked_at is not None or expires_at <= now or user.is_deleted:
            return None
        key_id = record.id
        record.last_used_at = now
        await self.session.commit()
        # AsyncSession expires ORM attributes on commit by default. Refresh the
        # user before returning it because the MCP auth middleware reads user.id
        # after this method completes; otherwise that synchronous attribute
        # access attempts an async lazy load and raises MissingGreenlet.
        await self.session.refresh(user)
        return AuthenticatedMCPPrincipal(user=user, key_id=key_id)
