from __future__ import annotations

import hashlib
from uuid import UUID

from sqlalchemy import BigInteger, bindparam, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from app.models import AppliedJob, Job, JobClick, SavedJob
from app.infra.url import add_utm_params


class JobNotFoundError(LookupError):
    pass


class UserJobService:
    """User-owned job state shared by REST and MCP transports."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _lock_user_job(self, user_id: UUID, job_id: UUID) -> None:
        digest = hashlib.sha256(f"user-job:{user_id}:{job_id}".encode()).digest()
        lock_key = int.from_bytes(digest[:8], byteorder="big", signed=True)
        await self.session.execute(
            select(func.pg_advisory_xact_lock(bindparam("user_job_lock_key", lock_key, type_=BigInteger)))
        )

    async def _active_job(self, job_id: UUID) -> Job:
        result = await self.session.execute(select(Job).where(Job.id == job_id, Job.is_active.is_(True)))
        job = result.scalar_one_or_none()
        if job is None:
            raise JobNotFoundError("Job not found")
        return job

    async def list_saved_ids(self, user_id: UUID) -> list[UUID]:
        result = await self.session.execute(
            select(SavedJob.job_id).where(SavedJob.user_id == user_id).order_by(SavedJob.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_applied_ids(self, user_id: UUID) -> list[UUID]:
        result = await self.session.execute(
            select(AppliedJob.job_id).where(AppliedJob.user_id == user_id).order_by(AppliedJob.applied_at.desc())
        )
        return list(result.scalars().all())

    async def list_saved(self, user_id: UUID, limit: int = 50) -> list[tuple[SavedJob, Job]]:
        result = await self.session.execute(
            select(SavedJob, Job)
            .join(Job, SavedJob.job_id == Job.id)
            .where(SavedJob.user_id == user_id)
            .order_by(SavedJob.created_at.desc())
            .limit(min(max(limit, 1), 50))
            .options(load_only(
                Job.id, Job.source, Job.title, Job.company, Job.location,
                Job.city, Job.state, Job.country, Job.apply_url,
                Job.job_category, Job.job_type, Job.work_mode, Job.posted_at, Job.is_active,
            ))
        )
        return [(row.SavedJob, row.Job) for row in result.all()]

    async def list_applied(self, user_id: UUID, limit: int = 50) -> list[tuple[AppliedJob, Job]]:
        result = await self.session.execute(
            select(AppliedJob, Job)
            .join(Job, AppliedJob.job_id == Job.id)
            .where(AppliedJob.user_id == user_id)
            .order_by(AppliedJob.applied_at.desc())
            .limit(min(max(limit, 1), 50))
        )
        return [(row.AppliedJob, row.Job) for row in result.all()]

    async def save(self, user_id: UUID, job_id: UUID) -> bool:
        await self._lock_user_job(user_id, job_id)
        await self._active_job(job_id)
        result = await self.session.execute(
            select(SavedJob).where(SavedJob.user_id == user_id, SavedJob.job_id == job_id)
        )
        if result.scalar_one_or_none() is not None:
            return False
        self.session.add(SavedJob(user_id=user_id, job_id=job_id))
        await self.session.commit()
        return True

    async def unsave(self, user_id: UUID, job_id: UUID) -> bool:
        result = await self.session.execute(
            select(SavedJob).where(SavedJob.user_id == user_id, SavedJob.job_id == job_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.commit()
        return True

    async def mark_applied(self, user_id: UUID, job_id: UUID) -> bool:
        await self._lock_user_job(user_id, job_id)
        await self._active_job(job_id)
        result = await self.session.execute(
            select(AppliedJob).where(AppliedJob.user_id == user_id, AppliedJob.job_id == job_id)
        )
        if result.scalar_one_or_none() is not None:
            return False
        self.session.add(AppliedJob(user_id=user_id, job_id=job_id))
        await self.session.commit()
        return True

    async def apply_from_mcp(self, user_id: UUID, job_id: UUID) -> tuple[str, bool]:
        await self._lock_user_job(user_id, job_id)
        job = await self._active_job(job_id)
        apply_url = self.mcp_apply_url(job)
        result = await self.session.execute(
            select(AppliedJob).where(AppliedJob.user_id == user_id, AppliedJob.job_id == job_id)
        )
        created = result.scalar_one_or_none() is None
        if created:
            self.session.add(AppliedJob(user_id=user_id, job_id=job_id))
        self._record_mcp_click(user_id, job_id)
        await self.session.commit()
        return apply_url, created

    async def get_application_link(self, user_id: UUID, job_id: UUID) -> str:
        """Record an MCP link request without changing applied state."""
        job = await self._active_job(job_id)
        apply_url = self.mcp_apply_url(job)
        self._record_mcp_click(user_id, job_id)
        await self.session.commit()
        return apply_url

    def _record_mcp_click(self, user_id: UUID, job_id: UUID) -> None:
        self.session.add(
            JobClick(
                user_id=user_id,
                job_id=job_id,
                utm_source="internnexus",
                utm_medium="mcp",
                utm_campaign="ai-agent",
            )
        )

    async def unmark_applied(self, user_id: UUID, job_id: UUID) -> bool:
        result = await self.session.execute(
            select(AppliedJob).where(AppliedJob.user_id == user_id, AppliedJob.job_id == job_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.commit()
        return True

    @staticmethod
    def mcp_apply_url(job: Job) -> str:
        return add_utm_params(job.apply_url, source="internnexus", medium="mcp", campaign="ai-agent")
