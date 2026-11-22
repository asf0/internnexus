"""Unit tests for the related-jobs endpoint and the 410 detail change.

Runs without a database: `get_db` is overridden and the repository class is
patched at both import sites (`app.api.jobs` for the existence check,
`app.services.jobs.related` for the candidate query), covering routing and
response shape only. Query behaviour (same-company first, active-only,
windowed) is covered by integration tests.
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


def _job(
    job_id=None,
    *,
    is_active: bool = True,
    company: str = "Acme",
    category: str | None = "engineering",
):
    from app.models import Job

    job = Job()
    job.id = job_id or uuid4()
    job.source = "greenhouse"
    job.title = "Backend Engineer"
    job.company = company
    job.location = "London, UK"
    job.city = "London"
    job.state = None
    job.country = "UK"
    job.apply_url = "https://example.com/apply"
    job.description_text = "<p>Build things</p>"
    job.job_category = category
    job.job_type = "full_time"
    job.work_mode = "hybrid"
    job.posted_at = datetime(2026, 9, 1, tzinfo=timezone.utc)
    job.is_active = is_active
    return job


def _detail_repo(job) -> AsyncMock:
    repo = AsyncMock()
    repo.get_detail_by_id.return_value = job
    return repo


def _related_repo(job, candidates: list) -> AsyncMock:
    repo = AsyncMock()
    repo.get_detail_by_id.return_value = job
    repo.get_related_candidates.return_value = candidates
    return repo


def test_related_returns_summaries_for_an_active_job(client) -> None:
    job = _job()
    other = _job(uuid4(), company="Other")
    repo = _related_repo(job, [other])

    with (
        patch("app.api.jobs.JobRepository", return_value=repo),
        patch("app.services.jobs.related.JobRepository", return_value=repo),
    ):
        response = client.get(f"/jobs/{job.id}/related")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == str(other.id)
    assert body["items"][0]["company"] == "Other"
    repo.get_related_candidates.assert_awaited_once_with(
        job_id=job.id, company="Acme", category="engineering", limit=10
    )


def test_related_for_unknown_job_is_404(client) -> None:
    repo = _detail_repo(None)

    with (
        patch("app.api.jobs.JobRepository", return_value=repo),
        patch("app.services.jobs.related.JobRepository", return_value=repo),
    ):
        assert client.get(f"/jobs/{uuid4()}/related").status_code == 404


def test_related_for_deactivated_job_is_410(client) -> None:
    repo = _detail_repo(_job(is_active=False))

    with (
        patch("app.api.jobs.JobRepository", return_value=repo),
        patch("app.services.jobs.related.JobRepository", return_value=repo),
    ):
        assert client.get(f"/jobs/{uuid4()}/related").status_code == 410


def test_detail_for_deactivated_job_is_410(client) -> None:
    """Known-but-deactivated jobs are gone, not never-existed."""
    job = _job(is_active=False)
    repo = _detail_repo(job)
    cache = AsyncMock()
    cache.get.return_value = None

    with patch("app.api.jobs.JobRepository", return_value=repo):
        response = client.get(f"/jobs/{job.id}", headers={"x-cache-bypass": "1"})

    assert response.status_code == 410


def test_detail_for_unknown_job_is_404(client) -> None:
    repo = _detail_repo(None)

    with patch("app.api.jobs.JobRepository", return_value=repo):
        assert client.get(f"/jobs/{uuid4()}").status_code == 404


def test_related_rejects_non_uuid(client) -> None:
    assert client.get("/jobs/not-a-uuid/related").status_code == 422
