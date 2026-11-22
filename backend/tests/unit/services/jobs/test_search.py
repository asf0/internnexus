from __future__ import annotations

from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.models import Job
from app.services.jobs.search import JobSearchParams, JobSearchService
from app.services.jobs.posted_within import POSTED_WITHIN_VALUES
from app.services.jobs.query_parser import parse_search_query


def test_posted_within_canonical_values_are_supported() -> None:
    service = JobSearchService(session=object())  # type: ignore[arg-type]

    for value in POSTED_WITHIN_VALUES:
        stmt = service._apply_filters(
            select(Job),
            JobSearchParams(posted_within=value, saved_only=False),
            valid_ids=[],
        )
        assert "jobs.posted_at" in str(stmt)


def test_legacy_posted_within_values_fall_back_to_default_window() -> None:
    service = JobSearchService(session=object())  # type: ignore[arg-type]

    for value in ("week", "month"):
        stmt = service._apply_filters(
            select(Job),
            JobSearchParams(posted_within=value, saved_only=False),
            valid_ids=[],
        )
        assert "jobs.posted_at" in str(stmt)


@pytest.mark.asyncio
async def test_keyword_search_stays_in_sql_without_expanding_matching_ids() -> None:
    service = JobSearchService(session=object())  # type: ignore[arg-type]

    stmt, valid_ids = service.build_filtered_stmt(JobSearchParams(search="software"))
    compiled = stmt.compile(dialect=postgresql.dialect())
    sql = str(compiled)

    assert valid_ids == []
    assert "jobs.search_vector @@ to_tsquery" in sql
    assert "ts_rank_cd" in sql
    assert "jobs.id IN" not in sql
    assert len(compiled.params) < 10


def test_embedding_is_deferred_from_normal_job_queries() -> None:
    assert Job.description_embedding.property.deferred is True
    sql = str(select(Job).compile(dialect=postgresql.dialect()))
    assert "description_embedding" not in sql


@pytest.mark.asyncio
async def test_search_page_projects_summary_columns_only() -> None:
    service = JobSearchService(session=object())  # type: ignore[arg-type]
    service.build_filtered_stmt = Mock(return_value=(select(Job), []))
    service._count_results = AsyncMock(return_value=0)
    captured: list[object] = []

    async def capture(stmt, page, page_size):  # noqa: ANN001, ARG001
        captured.append(stmt)
        return []

    service._paginate = capture  # type: ignore[method-assign]

    await service._execute_search(JobSearchParams())

    sql = str(captured[0].compile(dialect=postgresql.dialect()))
    assert "description_text" not in sql
    assert "description_embedding" not in sql
    assert service._cache_key(JobSearchParams()).startswith("jobs:v2:")


def test_large_ranked_id_filter_uses_one_array_parameter() -> None:
    service = JobSearchService(session=object())  # type: ignore[arg-type]
    ids = [UUID(int=index + 1) for index in range(40_000)]

    stmt = service._apply_filters(
        select(Job),
        JobSearchParams(),
        valid_ids=ids,
    )
    stmt = service._apply_ordering(stmt, valid_ids=ids)
    compiled = stmt.compile(dialect=postgresql.dialect())
    sql = str(compiled)

    assert "= ANY" in sql
    assert "array_position" in sql
    assert compiled.params["filter_job_ids"] == ids
    assert len(compiled.params) >= 1  # filter_job_ids + optional default recency cutoff


def test_default_recency_filter_when_no_posted_within_and_not_saved_only() -> None:
    service = JobSearchService(session=object())  # type: ignore[arg-type]
    stmt = service._apply_filters(
        select(Job),
        JobSearchParams(posted_within=None, saved_only=False),
        valid_ids=[],
    )
    compiled = stmt.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "posted_at >=" in sql.lower() or "posted_at >" in sql.lower()


def test_no_default_recency_filter_for_saved_only() -> None:
    service = JobSearchService(session=object())  # type: ignore[arg-type]
    stmt = service._apply_filters(
        select(Job),
        JobSearchParams(posted_within=None, saved_only=True),
        valid_ids=[],
    )
    compiled = stmt.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "posted_at >=" not in sql.lower() and "posted_at >" not in sql.lower()


def test_explicit_posted_within_overrides_default() -> None:
    service = JobSearchService(session=object())  # type: ignore[arg-type]
    stmt = service._apply_filters(
        select(Job),
        JobSearchParams(posted_within="7d", saved_only=False),
        valid_ids=[],
    )
    compiled = stmt.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "posted_at >=" in sql.lower() or "posted_at >" in sql.lower()


def test_posted_within_all_bypasses_filter() -> None:
    service = JobSearchService(session=object())  # type: ignore[arg-type]
    stmt = service._apply_filters(
        select(Job),
        JobSearchParams(posted_within="all", saved_only=False),
        valid_ids=[],
    )
    compiled = stmt.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "posted_at >=" not in sql.lower() and "posted_at >" not in sql.lower()


def test_ordinary_keyword_match_modes_build_all_or_any_queries() -> None:
    service = JobSearchService(session=object())  # type: ignore[arg-type]
    parsed = parse_search_query("python backend")

    assert service._build_tsquery("python backend", parsed, "all") == "python:* & backend:*"
    assert service._build_tsquery("python backend", parsed, "any") == "python:* | backend:*"


def test_explicit_boolean_operators_override_match_mode() -> None:
    service = JobSearchService(session=object())  # type: ignore[arg-type]

    explicit_or = service._build_tsquery(
        "python OR backend", parse_search_query("python OR backend"), "all"
    )
    explicit_and = service._build_tsquery(
        "python AND backend", parse_search_query("python AND backend"), "any"
    )

    assert " | " in explicit_or
    assert " & " in explicit_and


def test_match_mode_is_normalized_and_included_in_cache_key() -> None:
    service = JobSearchService(session=object())  # type: ignore[arg-type]
    invalid = JobSearchParams(search="python", match_mode="invalid")
    all_params = JobSearchParams(search="python", match_mode="all")
    any_params = JobSearchParams(search="python", match_mode="any")

    assert invalid.match_mode == "all"
    assert service._cache_key(all_params) != service._cache_key(any_params)


def test_count_cache_key_is_shared_across_pages() -> None:
    service = JobSearchService(session=object(), cache=object())  # type: ignore[arg-type]
    page_one = JobSearchParams(page=1, company="Acme")
    page_two = JobSearchParams(page=2, company="Acme")
    other_company = JobSearchParams(page=1, company="Other")

    assert service._count_cache_key(page_one) == service._count_cache_key(page_two)
    assert service._count_cache_key(page_one) != service._count_cache_key(other_company)
    assert service._count_cache_key(page_one).startswith("jobs:count:v1:")


class _FakeCache:
    """Minimal CacheService stand-in for count-sharing tests."""

    def __init__(self) -> None:
        self.data: dict[str, object] = {}

    async def get(self, key: str) -> object | None:
        return self.data.get(key)

    async def set(self, key: str, value: object, ttl: int = 3600) -> bool:
        self.data[key] = value
        return True


@pytest.mark.asyncio
async def test_count_is_cached_across_pages() -> None:
    cache = _FakeCache()
    service = JobSearchService(session=object(), cache=cache)  # type: ignore[arg-type]
    service.build_filtered_stmt = Mock(return_value=(select(Job), []))  # type: ignore[method-assign]
    service._apply_ordering = Mock(side_effect=lambda stmt, valid_ids: stmt)  # type: ignore[method-assign]
    service._count_results = AsyncMock(return_value=42)  # type: ignore[method-assign]

    async def fake_paginate(stmt, page, page_size):  # noqa: ANN001, ARG001
        return []

    service._paginate = fake_paginate  # type: ignore[method-assign]

    await service._execute_search(JobSearchParams(page=1, company="Acme"))
    await service._execute_search(JobSearchParams(page=2, company="Acme"))

    assert service._count_results.await_count == 1
    assert cache.data
