"""The public job endpoints must not validate a session for shared requests."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.infra.db import get_db
from app.main import app
from app.schemas.jobs import JobListResponse


@pytest.fixture
def client():
    async def _override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_list_jobs_skips_session_validation_without_saved_only(client) -> None:
    with (
        patch("app.api.jobs.get_job_search_service") as mock_get_service,
        patch("app.api.jobs.get_optional_user", new=AsyncMock()) as mock_optional_user,
    ):
        mock_service = AsyncMock()
        mock_service.search.return_value = JobListResponse(
            items=[], total=0, page=1, page_size=20
        )
        mock_get_service.return_value = mock_service

        response = client.get(
            "/jobs",
            headers={"Authorization": "Bearer not-a-real-token"},
        )

    assert response.status_code == 200
    mock_optional_user.assert_not_awaited()


def test_locations_skips_session_validation_without_saved_only(client) -> None:
    with (
        patch("app.api.jobs.get_cache_service") as mock_get_cache,
        patch("app.api.jobs.LocationService") as mock_location_service,
        patch("app.api.jobs.get_optional_user", new=AsyncMock()) as mock_optional_user,
    ):
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True
        mock_get_cache.return_value = mock_cache

        mock_service = AsyncMock()
        mock_service.get_location_hierarchy_from_filtered_jobs.return_value = []
        mock_location_service.return_value = mock_service

        response = client.get(
            "/jobs/filters/locations",
            headers={"Authorization": "Bearer not-a-real-token"},
        )

    assert response.status_code == 200
    mock_optional_user.assert_not_awaited()
