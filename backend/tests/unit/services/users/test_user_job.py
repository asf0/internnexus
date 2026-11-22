from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models import AppliedJob, Job, JobClick
from app.services.users.user_job import UserJobService


def scalar_result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def mock_session(*results):
    session = MagicMock()
    session.execute = AsyncMock(side_effect=results)
    session.commit = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_apply_from_mcp_locks_and_creates_state_and_one_click():
    user_id, job_id = uuid4(), uuid4()
    job = MagicMock(spec=Job)
    job.apply_url = "https://employer.example/apply"
    session = mock_session(
        MagicMock(),
        scalar_result(job),
        scalar_result(None),
    )

    apply_url, created = await UserJobService(session).apply_from_mcp(user_id, job_id)

    assert apply_url == (
        "https://employer.example/apply?utm_campaign=ai-agent&utm_medium=mcp&utm_source=internnexus"
    )
    assert created is True
    assert "pg_advisory_xact_lock" in str(session.execute.await_args_list[0].args[0])
    added = [call.args[0] for call in session.add.call_args_list]
    assert sum(isinstance(row, AppliedJob) for row in added) == 1
    assert sum(isinstance(row, JobClick) for row in added) == 1
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_apply_from_mcp_is_state_idempotent_but_records_each_link_request():
    user_id, job_id = uuid4(), uuid4()
    job = MagicMock(spec=Job)
    job.apply_url = "https://employer.example/apply"
    applied = MagicMock(spec=AppliedJob)
    session = mock_session(
        MagicMock(),
        scalar_result(job),
        scalar_result(applied),
    )

    apply_url, created = await UserJobService(session).apply_from_mcp(user_id, job_id)

    assert apply_url == (
        "https://employer.example/apply?utm_campaign=ai-agent&utm_medium=mcp&utm_source=internnexus"
    )
    assert created is False
    added = [call.args[0] for call in session.add.call_args_list]
    assert sum(isinstance(row, AppliedJob) for row in added) == 0
    assert sum(isinstance(row, JobClick) for row in added) == 1
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_application_link_records_click_without_applied_state():
    user_id, job_id = uuid4(), uuid4()
    job = MagicMock(spec=Job)
    job.apply_url = "https://employer.example/apply"
    session = mock_session(scalar_result(job))

    apply_url = await UserJobService(session).get_application_link(user_id, job_id)

    assert apply_url == (
        "https://employer.example/apply?utm_campaign=ai-agent&utm_medium=mcp&utm_source=internnexus"
    )
    added = [call.args[0] for call in session.add.call_args_list]
    assert not any(isinstance(row, AppliedJob) for row in added)
    clicks = [row for row in added if isinstance(row, JobClick)]
    assert len(clicks) == 1
    assert clicks[0].user_id == user_id
    assert clicks[0].job_id == job_id
    assert clicks[0].utm_medium == "mcp"
    assert clicks[0].utm_campaign == "ai-agent"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_application_link_reads_url_before_commit_expires_job():
    class ExpiringJob:
        def __init__(self):
            self.expired = False

        @property
        def apply_url(self):
            if self.expired:
                raise RuntimeError("expired ORM attribute accessed")
            return "https://employer.example/apply"

    user_id, job_id = uuid4(), uuid4()
    job = ExpiringJob()
    session = mock_session(scalar_result(job))

    async def expire_on_commit():
        job.expired = True

    session.commit.side_effect = expire_on_commit

    apply_url = await UserJobService(session).get_application_link(user_id, job_id)

    assert apply_url == (
        "https://employer.example/apply?utm_campaign=ai-agent&utm_medium=mcp&utm_source=internnexus"
    )
    assert job.expired is True


@pytest.mark.asyncio
async def test_apply_from_mcp_reads_url_before_commit_expires_job():
    class ExpiringJob:
        def __init__(self):
            self.expired = False

        @property
        def apply_url(self):
            if self.expired:
                raise RuntimeError("expired ORM attribute accessed")
            return "https://employer.example/apply"

    user_id, job_id = uuid4(), uuid4()
    job = ExpiringJob()
    session = mock_session(MagicMock(), scalar_result(job), scalar_result(None))

    async def expire_on_commit():
        job.expired = True

    session.commit.side_effect = expire_on_commit

    apply_url, created = await UserJobService(session).apply_from_mcp(user_id, job_id)

    assert created is True
    assert apply_url == (
        "https://employer.example/apply?utm_campaign=ai-agent&utm_medium=mcp&utm_source=internnexus"
    )
    assert job.expired is True
