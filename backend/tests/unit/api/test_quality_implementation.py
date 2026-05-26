"""Focused tests for backend quality implementation hardening."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.api.admin import _add_admin_audit_log, _commit_or_500
from app.api.admin_schemas import AdminJobBulkRequest
from app.models import AdminAuditLog


@pytest.mark.asyncio
async def test_commit_or_500_rolls_back_failed_transaction():
    db = AsyncMock()
    db.commit.side_effect = SQLAlchemyError("commit failed")

    with pytest.raises(HTTPException) as exc_info:
        await _commit_or_500(db, "test operation")

    assert exc_info.value.status_code == 500
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_admin_audit_log_records_actor_and_metadata():
    actor_id = uuid4()
    target_id = uuid4()
    db = AsyncMock()
    db.get.return_value = SimpleNamespace(email="admin@example.com")
    db.add = MagicMock()

    await _add_admin_audit_log(
        db,
        actor_user_id=actor_id,
        action="job.hard_delete",
        target_type="job",
        target_id=target_id,
        metadata={"reason": "test"},
    )

    db.get.assert_awaited_once()
    db.add.assert_called_once()
    audit_log = db.add.call_args.args[0]
    assert isinstance(audit_log, AdminAuditLog)
    assert audit_log.actor_user_id == actor_id
    assert audit_log.actor_email == "admin@example.com"
    assert audit_log.action == "job.hard_delete"
    assert audit_log.target_type == "job"
    assert audit_log.target_id == target_id
    assert audit_log.metadata_ == {"reason": "test"}


def test_admin_bulk_request_rejects_oversized_batches():
    with pytest.raises(ValidationError):
        AdminJobBulkRequest(job_ids=[uuid4() for _ in range(501)], action="deactivate")
