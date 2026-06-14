"""Shared helpers for admin API routers."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdminAuditLog, User

logger = logging.getLogger(__name__)

VALID_PIPELINE_STEPS = {"discover", "sync_inactive", "ingest", "delete_inactive", "cleanup", "classify", "embed"}


async def _commit_or_500(db: AsyncSession, operation: str) -> None:
    try:
        await db.commit()
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.exception("Database mutation failed during %s", operation)
        raise HTTPException(status_code=500, detail="Database operation failed") from exc


async def _add_admin_audit_log(
    db: AsyncSession,
    *,
    actor_user_id: UUID | None,
    action: str,
    target_type: str,
    target_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    actor_email = None
    if actor_user_id is not None:
        actor = await db.get(User, actor_user_id)
        actor_email = actor.email if actor else None
    db.add(
        AdminAuditLog(
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata_=metadata or {},
        )
    )
