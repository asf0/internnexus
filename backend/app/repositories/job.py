"""Job repository for database operations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import cast
from uuid import UUID

from sqlalchemy import and_, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only
from sqlalchemy.sql.elements import ColumnElement

from app.models import Job
from app.repositories.base import BaseRepository
from app.services.jobs.posted_within import DEFAULT_JOB_POSTED_WITHIN_DAYS


class JobRepository(BaseRepository[Job]):
    """Repository for Job model operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Job, session)

    async def get_detail_by_id(self, job_id: UUID) -> Job | None:
        """Fetch only fields used by the public detail response."""
        stmt = (
            select(Job)
            .where(Job.id == job_id)
            .options(
                load_only(
                    Job.id, Job.source, Job.title, Job.company, Job.location,
                    Job.city, Job.state, Job.country, Job.apply_url,
                    Job.description_text, Job.job_category, Job.job_type,
                    Job.work_mode, Job.posted_at, Job.is_active,
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _sitemap_filter() -> ColumnElement[bool]:
        """Rows the public job listing will actually serve.

        Must mirror JobSearchService's unfiltered listing, which is active-only
        and additionally windowed to DEFAULT_JOB_POSTED_WITHIN_DAYS (see
        app/services/jobs/search.py). Listing every active row instead would
        publish tens of thousands of URLs that the site links from nowhere.
        Note this also excludes undated jobs, since ``posted_at >= cutoff`` is
        never true for NULL.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=DEFAULT_JOB_POSTED_WITHIN_DAYS)
        return and_(Job.is_active.is_(True), Job.posted_at >= cutoff)

    async def count_sitemap_jobs(self) -> int:
        """Count the jobs a sitemap should list. Sizes the chunk set."""
        stmt = select(func.count()).select_from(Job).where(self._sitemap_filter())
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_sitemap_ids(self, limit: int, offset: int) -> list[tuple[UUID, datetime]]:
        """Get (id, posted_at) for listable jobs, for sitemap generation.

        The ordering must be total: sitemap chunks page through this with
        OFFSET, so a non-deterministic tie-break would duplicate rows in one
        chunk and drop them from another. ``id`` supplies that tie-break.
        """
        stmt = (
            select(Job.id, Job.posted_at)
            .where(self._sitemap_filter())
            .order_by(Job.posted_at.desc(), Job.id)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return [(row[0], cast(datetime, row[1])) for row in result.all()]

    async def get_related_candidates(
        self,
        job_id: UUID,
        company: str,
        category: str | None,
        limit: int,
    ) -> list[Job]:
        """Active jobs related to one job: same company first, then same category.

        Two index-backed queries instead of one ``OR`` + ``ORDER BY``. The
        single-statement form had to materialize every active row in the
        posting window before its top-N sort could run -- at production scale
        that was 471k rows per job-detail view. Each statement here matches a
        ``(company|job_category, posted_at DESC, id) WHERE is_active`` index
        and can stop after ``limit`` rows.

        Semantics are unchanged: company matches outrank category matches,
        recency and ``id`` break ties, and a job that matches both is returned
        once.
        """
        options = load_only(
            Job.id, Job.source, Job.title, Job.company, Job.location,
            Job.city, Job.state, Job.country, Job.apply_url,
            Job.job_category, Job.job_type, Job.work_mode, Job.posted_at,
            Job.is_active,
        )
        base = (
            select(Job)
            .where(self._sitemap_filter(), Job.id != job_id)
            .options(options)
        )

        rows = list(
            (
                await self.session.execute(
                    base.where(Job.company == company)
                    .order_by(Job.posted_at.desc(), Job.id)
                    .limit(limit)
                )
            ).scalars().all()
        )
        if len(rows) >= limit or category is None:
            return rows

        seen = {job.id for job in rows}
        category_rows = (
            await self.session.execute(
                base.where(Job.job_category == category, Job.company != company)
                .order_by(Job.posted_at.desc(), Job.id)
                .limit(limit)
            )
        ).scalars().all()
        for job in category_rows:
            if job.id in seen:
                continue
            rows.append(job)
            seen.add(job.id)
            if len(rows) >= limit:
                break
        return rows

    async def get_distinct_companies(self) -> list[str]:
        """Get all distinct company names."""
        stmt = select(distinct(Job.company)).where(Job.is_active.is_(True)).order_by(Job.company)
        result = await self.session.execute(stmt)
        return [cast(str, row[0]) for row in result.all() if row[0] is not None]

    async def get_distinct_categories(self) -> list[str]:
        """Get all distinct job categories."""
        stmt = (
            select(distinct(Job.job_category))
            .where(Job.job_category.isnot(None), Job.is_active.is_(True))
            .order_by(Job.job_category)
        )
        result = await self.session.execute(stmt)
        # job_category is now a string, no enum conversion needed
        return [cast(str, row[0]) for row in result.all() if row[0]]
