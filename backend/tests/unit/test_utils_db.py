"""Tests for shared database helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.utils.db import commit_or_500


@pytest.mark.asyncio
async def test_commit_or_500_commits_successfully():
    db = AsyncMock()

    await commit_or_500(db, operation="save job")

    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_commit_or_500_rolls_back_and_raises_500_on_failure():
    db = AsyncMock()
    db.commit.side_effect = SQLAlchemyError("commit failed")

    with pytest.raises(HTTPException) as exc_info:
        await commit_or_500(db, operation="save job")

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Failed to save job"
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_commit_or_500_uses_custom_detail():
    db = AsyncMock()
    db.commit.side_effect = SQLAlchemyError("commit failed")

    with pytest.raises(HTTPException) as exc_info:
        await commit_or_500(db, operation="grant admin", detail="Database operation failed")

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Database operation failed"
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_commit_or_500_default_detail_includes_operation():
    db = AsyncMock()
    db.commit.side_effect = SQLAlchemyError("commit failed")

    with pytest.raises(HTTPException) as exc_info:
        await commit_or_500(db, operation="track job click")

    assert exc_info.value.detail == "Failed to track job click"
