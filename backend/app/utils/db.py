"""Shared database helpers for API routes."""

from __future__ import annotations

import logging

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def commit_or_500(
    db: AsyncSession,
    *,
    operation: str,
    detail: str | None = None,
) -> None:
    """Commit the current transaction, rolling back and raising 500 on failure.

    Args:
        db: The active async SQLAlchemy session.
        operation: Human-readable name of the operation, used for logging and
            the default error message.
        detail: Optional override for the HTTPException detail. If omitted,
            the detail is ``f"Failed to {operation}"``.

    Raises:
        HTTPException: 500 with a safe detail string if commit fails.
    """
    try:
        await db.commit()
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.exception("Database mutation failed during %s", operation)
        message = detail if detail is not None else f"Failed to {operation}"
        raise HTTPException(status_code=500, detail=message) from exc
