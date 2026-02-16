"""Job repository for database operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job
from app.repositories.base import BaseRepository


class JobRepository(BaseRepository[Job]):
    """Repository for Job model operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Job, session)

    async def get_active_jobs(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Job]:
        """Get all active jobs with pagination."""
        stmt = (
            select(Job)
            .where(Job.is_active == True)  # noqa: E712
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_fingerprint(self, fingerprint: str) -> Job | None:
        """Get a job by its unique fingerprint."""
        stmt = select(Job).where(Job.fingerprint == fingerprint)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_distinct_companies(self) -> list[str]:
        """Get all distinct company names."""
        stmt = (
            select(distinct(Job.company))
            .where(Job.is_active == True)  # noqa: E712
            .order_by(Job.company)
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def get_distinct_locations(self) -> list[str]:
        """Get all distinct locations."""
        stmt = (
            select(distinct(Job.location))
            .where(Job.is_active == True, Job.location.isnot(None))  # noqa: E712
            .order_by(Job.location)
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all() if row[0]]

    async def get_distinct_categories(self) -> list[str]:
        """Get all distinct job categories."""
        stmt = (
            select(distinct(Job.job_category))
            .where(Job.is_active == True, Job.job_category.isnot(None))  # noqa: E712
            .order_by(Job.job_category)
        )
        result = await self.session.execute(stmt)
        # Convert enum values to their string values for JSON serialization
        return [
            row[0].value if hasattr(row[0], "value") else row[0] for row in result.all() if row[0]
        ]

    async def get_jobs_by_ids(self, ids: list[UUID]) -> list[Job]:
        """Get jobs by a list of IDs."""
        if not ids:
            return []
        stmt = select(Job).where(Job.id.in_(ids), Job.is_active == True)  # noqa: E712
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_jobs_without_embeddings(self) -> int:
        """Count jobs that don't have embeddings."""
        stmt = (
            select(func.count())
            .select_from(Job)
            .where(Job.is_active == True, Job.description_embedding.is_(None))  # noqa: E712
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def get_jobs_without_embeddings(self, limit: int = 100) -> list[Job]:
        """Get jobs that don't have embeddings."""
        stmt = (
            select(Job)
            .where(Job.is_active == True, Job.description_embedding.is_(None))  # noqa: E712
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
