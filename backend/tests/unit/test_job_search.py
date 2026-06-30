from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.models import Job
from app.services.job_search import JobSearchParams, JobSearchService
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


@pytest.mark.asyncio
async def test_keyword_search_stays_in_sql_without_expanding_matching_ids() -> None:
    service = JobSearchService(session=object())  # type: ignore[arg-type]

    stmt, valid_ids, result_order = await service.build_filtered_stmt(JobSearchParams(search="software"))
    compiled = stmt.compile(dialect=postgresql.dialect())
    sql = str(compiled)

    assert valid_ids == []
    assert result_order == []
    assert "jobs.search_vector @@ to_tsquery" in sql
    assert "ts_rank_cd" in sql
    assert "jobs.id IN" not in sql
    assert len(compiled.params) < 10


def test_large_ranked_id_filter_uses_one_array_parameter() -> None:
    service = JobSearchService(session=object())  # type: ignore[arg-type]
    ids = [UUID(int=index + 1) for index in range(40_000)]

    stmt = service._apply_filters(
        select(Job),
        JobSearchParams(),
        valid_ids=ids,
        result_order=[],
    )
    stmt = service._apply_ordering(stmt, valid_ids=ids, result_order=[])
    compiled = stmt.compile(dialect=postgresql.dialect())
    sql = str(compiled)

    assert "= ANY" in sql
    assert "array_position" in sql
    assert len(compiled.params) == 1
    assert compiled.params["filter_job_ids"] == ids
