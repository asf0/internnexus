"""Integration tests for the single-query location facet aggregation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, JobSource
from app.services.jobs.location import LocationService


def _job(country: str | None, state: str | None, city: str | None, count: int) -> list[Job]:
    now = datetime.now(timezone.utc)
    jobs = []
    for index in range(count):
        jobs.append(
            Job(
                id=uuid4(),
                fingerprint=f"facet-{uuid4()}",
                source=JobSource.greenhouse,
                title=f"Facet {index}",
                company="Facet Co",
                location=city or state or country or "Remote",
                city=city,
                state=state,
                country=country,
                apply_url="https://example.com/apply",
                description_text="Facet test job",
                posted_at=now - timedelta(days=1),
                is_active=True,
            )
        )
    return jobs


@pytest.mark.integration
class TestLocationHierarchy:
    async def test_rolls_leaf_groups_up_into_country_and_state(
        self, db_session: AsyncSession
    ) -> None:
        jobs = [
            *_job("USA", "CA", "San Francisco", 12),
            *_job("USA", "CA", "Los Angeles", 11),
            *_job("USA", "NY", "New York", 5),
            *_job("Canada", "ON", "Toronto", 10),
        ]
        for job in jobs:
            db_session.add(job)
        await db_session.commit()

        stmt = select(Job).where(Job.is_active.is_(True))
        locations = await LocationService(db_session).get_location_hierarchy_from_filtered_jobs(stmt)

        assert [entry["value"] for entry in locations] == ["Canada", "USA"]
        usa = locations[1]
        assert usa["count"] == 28
        assert [entry["value"] for entry in usa["children"]] == ["CA", "NY"]
        assert usa["children"][0]["count"] == 23
        assert [entry["value"] for entry in usa["children"][0]["children"]] == [
            "Los Angeles",
            "San Francisco",
        ]

    async def test_respects_the_filters_in_the_incoming_statement(
        self, db_session: AsyncSession
    ) -> None:
        for job in [*_job("USA", "CA", "San Francisco", 12), *_job("Canada", "ON", "Toronto", 12)]:
            db_session.add(job)
        await db_session.commit()

        stmt = select(Job).where(Job.is_active.is_(True), Job.country == "USA")
        locations = await LocationService(db_session).get_location_hierarchy_from_filtered_jobs(stmt)

        assert [entry["value"] for entry in locations] == ["USA"]
