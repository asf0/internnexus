from __future__ import annotations

from sqlalchemy import select

from app.models import Job
from app.services.job_search import JobSearchService
from app.services.posted_within import POSTED_WITHIN_VALUES


def test_posted_within_canonical_values_are_supported() -> None:
    service = JobSearchService(session=object())  # type: ignore[arg-type]
    stmt = select(Job)

    for value in POSTED_WITHIN_VALUES:
        filtered = service._apply_posted_within_filter(stmt, value)
        assert filtered is not stmt
        assert "jobs.posted_at" in str(filtered)


def test_legacy_posted_within_values_are_ignored() -> None:
    service = JobSearchService(session=object())  # type: ignore[arg-type]
    stmt = select(Job)

    assert service._apply_posted_within_filter(stmt, "week") is stmt
    assert service._apply_posted_within_filter(stmt, "month") is stmt
