"""Integration tests for related-job candidate selection.

Routing and response shape are covered without a database in
tests/unit/api/test_jobs_related.py. What needs a real database is the
ordering contract: same-company rows outrank same-category rows, ties are
deterministic, and the source/inactive/stale rows are excluded.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, JobSource
from app.repositories.job import JobRepository
from app.services.jobs.posted_within import DEFAULT_JOB_POSTED_WITHIN_DAYS


def _job(
    *,
    title: str,
    company: str,
    category: str | None,
    posted_days_ago: int,
    is_active: bool = True,
) -> Job:
    now = datetime.now(timezone.utc)
    return Job(
        id=uuid4(),
        fingerprint=f"related-{uuid4()}",
        source=JobSource.greenhouse,
        title=title,
        company=company,
        location="Remote",
        apply_url="https://example.com/apply",
        description_text="Related test job",
        job_category=category,
        posted_at=now - timedelta(days=posted_days_ago),
        is_active=is_active,
    )


@pytest.mark.integration
class TestRelatedCandidates:
    @pytest.fixture
    async def seeded(self, db_session: AsyncSession):
        source = _job(
            title="Source",
            company="Acme",
            category="engineering",
            posted_days_ago=0,
        )
        same_company = [
            _job(title="Acme Newest", company="Acme", category=None, posted_days_ago=1),
            _job(title="Acme Middle", company="Acme", category="engineering", posted_days_ago=2),
            _job(title="Acme Oldest", company="Acme", category=None, posted_days_ago=3),
        ]
        same_category = [
            _job(title="Other Category Newer", company="Other", category="engineering", posted_days_ago=4),
            _job(title="Other Category Older", company="Another", category="engineering", posted_days_ago=5),
        ]
        excluded = [
            _job(title="Inactive", company="Acme", category="engineering", posted_days_ago=1, is_active=False),
            _job(
                title="Stale",
                company="Acme",
                category="engineering",
                posted_days_ago=DEFAULT_JOB_POSTED_WITHIN_DAYS + 1,
            ),
            _job(title="Unrelated", company="Nope", category="sales", posted_days_ago=1),
        ]

        for job in [source, *same_company, *same_category, *excluded]:
            db_session.add(job)
        await db_session.commit()

        return {
            "source": source,
            "same_company_ids": [job.id for job in same_company],
            "same_category_ids": [job.id for job in same_category],
            "excluded_ids": {job.id for job in excluded},
        }

    async def test_company_matches_outrank_category_matches(
        self, db_session: AsyncSession, seeded
    ) -> None:
        repo = JobRepository(db_session)
        rows = await repo.get_related_candidates(
            job_id=seeded["source"].id,
            company="Acme",
            category="engineering",
            limit=10,
        )

        assert [job.id for job in rows] == [
            *seeded["same_company_ids"],
            *seeded["same_category_ids"],
        ]

    async def test_source_inactive_stale_and_unrelated_are_excluded(
        self, db_session: AsyncSession, seeded
    ) -> None:
        repo = JobRepository(db_session)
        rows = await repo.get_related_candidates(
            job_id=seeded["source"].id,
            company="Acme",
            category="engineering",
            limit=10,
        )

        ids = {job.id for job in rows}
        assert seeded["source"].id not in ids
        assert ids.isdisjoint(seeded["excluded_ids"])

    async def test_company_rows_are_returned_once_and_first(
        self, db_session: AsyncSession, seeded
    ) -> None:
        """A job matching both filters must not appear twice."""
        repo = JobRepository(db_session)
        rows = await repo.get_related_candidates(
            job_id=seeded["source"].id,
            company="Acme",
            category="engineering",
            limit=10,
        )

        ids = [job.id for job in rows]
        assert len(ids) == len(set(ids))
        # "Acme Middle" matches both company and category; it must be in the
        # company block, not repeated from the category query.
        assert ids.index(seeded["same_company_ids"][1]) < len(seeded["same_company_ids"])

    async def test_limit_shorter_than_company_count_returns_only_company(
        self, db_session: AsyncSession, seeded
    ) -> None:
        repo = JobRepository(db_session)
        rows = await repo.get_related_candidates(
            job_id=seeded["source"].id,
            company="Acme",
            category="engineering",
            limit=2,
        )

        assert [job.id for job in rows] == seeded["same_company_ids"][:2]

    async def test_missing_category_returns_only_company_matches(
        self, db_session: AsyncSession, seeded
    ) -> None:
        repo = JobRepository(db_session)
        rows = await repo.get_related_candidates(
            job_id=seeded["source"].id,
            company="Acme",
            category=None,
            limit=10,
        )

        assert [job.id for job in rows] == seeded["same_company_ids"]
