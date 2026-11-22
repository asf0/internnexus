"""Unit tests for the sitemap id endpoint.

These run without a database: `get_db` is overridden and the repository is
patched, so they cover routing and request/response shape only. Query
behaviour (ordering, active-only filtering) is covered by
tests/integration/test_jobs_api.py.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.infra.db import get_db
from app.main import app


@pytest.fixture
def client():
    async def _override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def _repo(total: int = 0, rows: list | None = None) -> AsyncMock:
    repo = AsyncMock()
    repo.count_sitemap_jobs.return_value = total
    repo.get_sitemap_ids.return_value = rows or []
    return repo


def test_sitemap_ids_route_is_not_shadowed_by_the_job_detail_route(client) -> None:
    """`/jobs/sitemap-ids` must be declared above `/jobs/{job_id}`.

    Regression guard: if it is ever reordered below, FastAPI matches the
    dynamic route first and rejects "sitemap-ids" as an invalid UUID with a
    422 instead of serving the sitemap payload.
    """
    with patch("app.api.jobs.JobRepository", return_value=_repo(total=7)):
        response = client.get("/jobs/sitemap-ids?limit=0")

    assert response.status_code == 200
    assert response.json()["total"] == 7

    # The dynamic route is still reachable and still validates UUIDs.
    assert client.get("/jobs/not-a-uuid").status_code == 422


def test_limit_zero_returns_the_count_without_querying_ids(client) -> None:
    """generateSitemaps only needs the total to size its chunk set."""
    repo = _repo(total=245644)

    with patch("app.api.jobs.JobRepository", return_value=repo):
        response = client.get("/jobs/sitemap-ids?limit=0")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 245644}
    repo.get_sitemap_ids.assert_not_awaited()


def test_returns_id_and_posted_at_pairs(client) -> None:
    job_id = uuid4()
    posted_at = datetime(2026, 7, 3, 12, 0, tzinfo=timezone.utc)
    repo = _repo(total=1, rows=[(job_id, posted_at)])

    with patch("app.api.jobs.JobRepository", return_value=repo):
        response = client.get("/jobs/sitemap-ids?limit=50000&offset=0")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"] == [{"id": str(job_id), "posted_at": "2026-07-03T12:00:00Z"}]


def test_null_posted_at_is_tolerated(client) -> None:
    """The query's date window excludes undated jobs, but the contract stays
    permissive: a null must serialise rather than 500, and the sitemap then
    omits lastModified for that entry."""
    job_id = uuid4()
    repo = _repo(total=1, rows=[(job_id, None)])

    with patch("app.api.jobs.JobRepository", return_value=repo):
        response = client.get("/jobs/sitemap-ids?limit=1")

    assert response.status_code == 200
    assert response.json()["items"][0]["posted_at"] is None


def test_limit_and_offset_are_forwarded_to_the_repository(client) -> None:
    repo = _repo(total=245644)

    with patch("app.api.jobs.JobRepository", return_value=repo):
        client.get("/jobs/sitemap-ids?limit=50000&offset=100000")

    repo.get_sitemap_ids.assert_awaited_once_with(limit=50000, offset=100000)


@pytest.mark.parametrize(
    "query",
    [
        "limit=50001",  # above the sitemap protocol's 50k cap
        "limit=-1",
        "offset=-1",
    ],
)
def test_out_of_range_parameters_are_rejected(client, query: str) -> None:
    with patch("app.api.jobs.JobRepository", return_value=_repo()):
        assert client.get(f"/jobs/sitemap-ids?{query}").status_code == 422
