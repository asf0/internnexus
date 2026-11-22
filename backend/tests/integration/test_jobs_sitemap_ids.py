"""Integration tests for the sitemap id query against a real database.

Routing and response shape are covered without a DB in
tests/unit/api/test_jobs_sitemap_ids.py. What needs a real database is the
query itself: that its filter matches what the public listing serves, and the
total ordering that lets sitemap chunks page with OFFSET without duplicating
or dropping rows.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, JobSource
from app.repositories.job import JobRepository
from app.services.jobs.posted_within import DEFAULT_JOB_POSTED_WITHIN_DAYS


def _job(*, title: str, posted_at: datetime | None, is_active: bool = True) -> Job:
    return Job(
        id=uuid4(),
        fingerprint=f"sitemap-{uuid4()}",
        source=JobSource.greenhouse,
        title=title,
        company="Sitemap Test Co",
        location="Remote",
        apply_url="https://example.com/apply",
        description_text="Sitemap test job",
        posted_at=posted_at,
        is_active=is_active,
    )


@pytest.mark.integration
class TestSitemapIds:
    @pytest.fixture
    async def seeded(self, db_session: AsyncSession):
        """Six listable jobs, plus four the public listing would never show."""
        now = datetime.now(timezone.utc)
        listable = [_job(title=f"Recent {i}", posted_at=now - timedelta(days=i)) for i in range(6)]
        excluded = [
            # Outside the listing's DEFAULT_JOB_POSTED_WITHIN_DAYS window.
            _job(
                title="Stale",
                posted_at=now - timedelta(days=DEFAULT_JOB_POSTED_WITHIN_DAYS + 5),
            ),
            # `posted_at >= cutoff` is never true for NULL.
            _job(title="Undated", posted_at=None),
            _job(title="Inactive recent", posted_at=now, is_active=False),
            _job(title="Inactive undated", posted_at=None, is_active=False),
        ]

        for job in [*listable, *excluded]:
            db_session.add(job)
        await db_session.commit()

        return {"listable_ids": {j.id for j in listable}}

    async def test_scope_matches_what_the_public_listing_serves(
        self, db_session: AsyncSession, seeded
    ) -> None:
        """Inactive, undated, and out-of-window jobs must all be excluded.

        Publishing them would advertise URLs the site links from nowhere.
        """
        repo = JobRepository(db_session)

        assert await repo.count_sitemap_jobs() == 6

        rows = await repo.get_sitemap_ids(limit=50, offset=0)
        assert {row[0] for row in rows} == seeded["listable_ids"]

    async def test_orders_newest_first(self, db_session: AsyncSession, seeded) -> None:
        repo = JobRepository(db_session)
        rows = await repo.get_sitemap_ids(limit=50, offset=0)

        posted = [row[1] for row in rows]
        assert posted == sorted(posted, reverse=True)
        assert all(row[1] is not None for row in rows)

    async def test_offset_paging_neither_duplicates_nor_drops_rows(
        self, db_session: AsyncSession, seeded
    ) -> None:
        """The guarantee sitemap chunking depends on.

        Without a total ordering, two OFFSET slices can overlap on ties and
        silently lose rows that fall between them.
        """
        repo = JobRepository(db_session)

        first = await repo.get_sitemap_ids(limit=2, offset=0)
        second = await repo.get_sitemap_ids(limit=2, offset=2)
        third = await repo.get_sitemap_ids(limit=2, offset=4)

        paged = [row[0] for row in (*first, *second, *third)]
        assert len(paged) == 6
        assert len(set(paged)) == 6
        assert set(paged) == seeded["listable_ids"]

    async def test_ties_on_posted_at_still_page_deterministically(
        self, db_session: AsyncSession
    ) -> None:
        """Identical timestamps are the case a naive ORDER BY gets wrong."""
        same_instant = datetime.now(timezone.utc) - timedelta(days=1)
        tied = [_job(title=f"Tied {i}", posted_at=same_instant) for i in range(6)]
        for job in tied:
            db_session.add(job)
        await db_session.commit()

        repo = JobRepository(db_session)
        paged = [
            row[0]
            for offset in (0, 2, 4)
            for row in await repo.get_sitemap_ids(limit=2, offset=offset)
        ]

        assert len(set(paged)) == 6
        assert set(paged) == {j.id for j in tied}

    async def test_repeated_calls_return_a_stable_order(
        self, db_session: AsyncSession, seeded
    ) -> None:
        repo = JobRepository(db_session)

        first = [row[0] for row in await repo.get_sitemap_ids(limit=50, offset=0)]
        second = [row[0] for row in await repo.get_sitemap_ids(limit=50, offset=0)]

        assert first == second

    async def test_offset_past_the_end_returns_empty(
        self, db_session: AsyncSession, seeded
    ) -> None:
        repo = JobRepository(db_session)

        assert await repo.get_sitemap_ids(limit=50, offset=1000) == []
