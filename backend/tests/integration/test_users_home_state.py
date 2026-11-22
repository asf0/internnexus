"""Integration tests for the one-query homepage user state."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AppliedJob, Job, JobSource, SavedJob, User, UserNotification
from app.services.users.home_state import HomeStateService


def _job() -> Job:
    return Job(
        id=uuid4(),
        fingerprint=f"home-state-{uuid4()}",
        source=JobSource.greenhouse,
        title="Home state job",
        company="Home Co",
        location="Remote",
        apply_url="https://example.com/apply",
        description_text="Home state test job",
        posted_at=datetime.now(timezone.utc),
        is_active=True,
    )


def _user() -> User:
    return User(id=uuid4(), email=f"home-state-{uuid4()}@example.com")


@pytest.mark.integration
class TestHomeState:
    async def test_returns_unread_count_and_membership_ids(
        self, db_session: AsyncSession
    ) -> None:
        user = _user()
        saved_job = _job()
        applied_job = _job()
        db_session.add_all(
            [
                user,
                saved_job,
                applied_job,
                UserNotification(
                    id=uuid4(), user_id=user.id, type="unread", payload={}, is_read=False
                ),
                UserNotification(
                    id=uuid4(), user_id=user.id, type="read", payload={}, is_read=True
                ),
                SavedJob(id=uuid4(), user_id=user.id, job_id=saved_job.id),
                AppliedJob(id=uuid4(), user_id=user.id, job_id=applied_job.id),
            ]
        )
        await db_session.commit()

        state = await HomeStateService(db_session).get(user.id)

        assert state.unread_count == 1
        assert state.saved_job_ids == [saved_job.id]
        assert state.applied_job_ids == [applied_job.id]

    async def test_empty_user_state_is_zero_and_empty_lists(
        self, db_session: AsyncSession
    ) -> None:
        user = _user()
        db_session.add(user)
        await db_session.commit()

        state = await HomeStateService(db_session).get(user.id)

        assert state.unread_count == 0
        assert state.saved_job_ids == []
        assert state.applied_job_ids == []
