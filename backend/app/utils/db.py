"""Shared database helpers for API routes."""

from __future__ import annotations

import logging
from collections.abc import Callable

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def commit_or_500(
    db: AsyncSession,
    *,
    operation: str,
    detail: str | None = None,
    error_mapper: Callable[[SQLAlchemyError], HTTPException | None] | None = None,
) -> None:
    """Commit the current transaction, rolling back and raising 500 on failure.

    Args:
        db: The active async SQLAlchemy session.
        operation: Human-readable name of the operation, used for logging and
            the default error message.
        detail: Optional override for the HTTPException detail. If omitted,
            the detail is ``f"Failed to {operation}"``.
        error_mapper: Optional route-specific mapper for preserving existing
            HTTP behavior for known database errors.

    Raises:
        HTTPException: 500 with a safe detail string if commit fails.
    """
    try:
        await db.commit()
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.exception("Database mutation failed during %s", operation)
        if error_mapper is not None:
            mapped_error = error_mapper(exc)
            if mapped_error is not None:
                raise mapped_error from exc
        message = detail if detail is not None else f"Failed to {operation}"
        raise HTTPException(status_code=500, detail=message) from exc


async def rollback_or_500(
    db: AsyncSession,
    *,
    operation: str,
    detail: str | None = None,
) -> None:
    """Rollback the current transaction, raising 500 if rollback itself fails."""
    try:
        await db.rollback()
    except SQLAlchemyError as exc:
        logger.exception("Database rollback failed during %s", operation)
        message = detail if detail is not None else f"Failed to {operation}"
        raise HTTPException(status_code=500, detail=message) from exc
