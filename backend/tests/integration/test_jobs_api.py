"""Integration tests for jobs API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone


class TestJobsAPI:
    """Test suite for jobs API endpoints."""

    @pytest.mark.asyncio
    async def test_list_jobs_success(self, client):
        """Test listing jobs with default parameters."""
        # Arrange
        with patch("app.api.jobs.get_job_search_service") as mock_get_service:
            mock_service = AsyncMock()
            from app.api.schemas import JobListResponse, JobResponse

            job = JobResponse(
                id=uuid4(),
                source="greenhouse",
                title="Software Engineer",
                company="TechCorp",
                location="San Francisco, CA",
                city="San Francisco",
                state="CA",
                country="USA",
                apply_url="https://example.com/apply",
                description_text="Great job opportunity",
                job_category="software_engineering",
                job_type="internship",
                work_mode="hybrid",
                posted_at=datetime.now(timezone.utc),
                is_active=True,
            )

            mock_service.search.return_value = JobListResponse(
                items=[job], total=1, page=1, page_size=20
            )
            mock_get_service.return_value = mock_service

            # Act
            response = await client.get("/jobs")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Software Engineer"

    @pytest.mark.asyncio
    async def test_list_jobs_with_filters(self, client):
        """Test listing jobs with filters."""
        # Arrange
        with patch("app.api.jobs.get_job_search_service") as mock_get_service:
            mock_service = AsyncMock()
            from app.api.schemas import JobListResponse, JobResponse

            mock_service.search.return_value = JobListResponse(
                items=[], total=0, page=1, page_size=20
            )
            mock_get_service.return_value = mock_service

            # Act
            response = await client.get("/jobs?search=python&location=remote&job_type=internship")

        # Assert
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_jobs_pagination(self, client):
        """Test jobs pagination."""
        # Arrange
        with patch("app.api.jobs.get_job_search_service") as mock_get_service:
            mock_service = AsyncMock()
            from app.api.schemas import JobListResponse

            mock_service.search.return_value = JobListResponse(
                items=[], total=100, page=2, page_size=50
            )
            mock_get_service.return_value = mock_service

            # Act
            response = await client.get("/jobs?page=2&page_size=50")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 50

    @pytest.mark.asyncio
    async def test_list_jobs_invalid_page_size(self, client):
        """Test listing jobs with invalid page size."""
        # Act
        response = await client.get("/jobs?page_size=200")  # Max is 100

        # Assert
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_job_success(self, client):
        """Test getting a single job by ID."""
        # Arrange
        job_id = str(uuid4())

        with (
            patch("app.api.jobs.get_redis_service") as mock_get_cache,
            patch("app.api.jobs.JobRepository") as mock_repo_class,
        ):
            # Mock cache miss
            mock_cache = AsyncMock()
            mock_cache.get.return_value = None
            mock_get_cache.return_value = mock_cache

            # Mock DB hit
            mock_repo = AsyncMock()
            mock_job = MagicMock()
            mock_job.id = uuid4()
            mock_job.source = "greenhouse"
            mock_job.title = "Software Engineer"
            mock_job.company = "TechCorp"
            mock_job.location = "San Francisco, CA"
            mock_job.city = "San Francisco"
            mock_job.state = "CA"
            mock_job.country = "USA"
            mock_job.apply_url = "https://example.com/apply"
            mock_job.description_text = "Great job"
            mock_job.job_category = None
            mock_job.job_type = None
            mock_job.work_mode = None
            mock_job.posted_at = None
            mock_job.is_active = True
            mock_repo.get_by_id.return_value = mock_job
            mock_repo_class.return_value = mock_repo

            # Act
            response = await client.get(f"/jobs/{job_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Software Engineer"

    @pytest.mark.asyncio
    async def test_get_job_from_cache(self, client):
        """Test getting a job from cache."""
        # Arrange
        job_id = str(uuid4())

        with patch("app.api.jobs.get_redis_service") as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.get.return_value = {
                "id": job_id,
                "source": "greenhouse",
                "title": "Cached Job",
                "company": "CacheCorp",
                "location": "Remote",
                "city": None,
                "state": None,
                "country": None,
                "apply_url": "https://example.com",
                "description_text": "Cached description",
                "job_category": None,
                "job_type": None,
                "work_mode": None,
                "posted_at": None,
                "is_active": True,
            }
            mock_get_cache.return_value = mock_cache

            # Act
            response = await client.get(f"/jobs/{job_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Cached Job"

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, client):
        """Test getting a non-existent job."""
        # Arrange
        job_id = str(uuid4())

        with (
            patch("app.api.jobs.get_redis_service") as mock_get_cache,
            patch("app.api.jobs.JobRepository") as mock_repo_class,
        ):
            mock_cache = AsyncMock()
            mock_cache.get.return_value = None
            mock_get_cache.return_value = mock_cache

            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_class.return_value = mock_repo

            # Act
            response = await client.get(f"/jobs/{job_id}")

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_job_invalid_id(self, client):
        """Test getting a job with invalid ID format."""
        # Act
        response = await client.get("/jobs/invalid-uuid")

        # Assert
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_job_inactive(self, client):
        """Test getting an inactive job."""
        # Arrange
        job_id = str(uuid4())

        with (
            patch("app.api.jobs.get_redis_service") as mock_get_cache,
            patch("app.api.jobs.JobRepository") as mock_repo_class,
        ):
            mock_cache = AsyncMock()
            mock_cache.get.return_value = None
            mock_get_cache.return_value = mock_cache

            mock_repo = AsyncMock()
            mock_job = MagicMock()
            mock_job.is_active = False
            mock_repo.get_by_id.return_value = mock_job
            mock_repo_class.return_value = mock_repo

            # Act
            response = await client.get(f"/jobs/{job_id}")

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_companies(self, client):
        """Test getting list of companies."""
        # Arrange
        with (
            patch("app.api.jobs.get_redis_service") as mock_get_cache,
            patch("app.api.jobs.JobRepository") as mock_repo_class,
        ):
            mock_cache = AsyncMock()
            mock_cache.get.return_value = None
            mock_get_cache.return_value = mock_cache

            mock_repo = AsyncMock()
            mock_repo.get_distinct_companies.return_value = ["Google", "Microsoft", "Amazon"]
            mock_repo_class.return_value = mock_repo

            # Act
            response = await client.get("/jobs/filters/companies")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "Google" in data
        assert "Microsoft" in data

    @pytest.mark.asyncio
    async def test_get_companies_cached(self, client):
        """Test getting companies from cache."""
        # Arrange
        with patch("app.api.jobs.get_redis_service") as mock_get_cache:
            mock_cache = AsyncMock()
            mock_cache.get.return_value = ["Cached Company"]
            mock_get_cache.return_value = mock_cache

            # Act
            response = await client.get("/jobs/filters/companies")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data == ["Cached Company"]

    @pytest.mark.asyncio
    async def test_get_categories(self, client):
        """Test getting list of job categories."""
        # Arrange
        with (
            patch("app.api.jobs.get_redis_service") as mock_get_cache,
            patch("app.api.jobs.JobRepository") as mock_repo_class,
        ):
            mock_cache = AsyncMock()
            mock_cache.get.return_value = None
            mock_get_cache.return_value = mock_cache

            mock_repo = AsyncMock()
            mock_repo.get_distinct_categories.return_value = [
                "software_engineering",
                "data_science_ai",
            ]
            mock_repo_class.return_value = mock_repo

            # Act
            response = await client.get("/jobs/filters/categories")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "software_engineering" in data

    @pytest.mark.asyncio
    async def test_get_locations(self, client):
        """Test getting location hierarchy."""
        # Arrange
        with (
            patch("app.api.jobs.get_redis_service") as mock_get_cache,
            patch("app.api.jobs.LocationService") as mock_service_class,
        ):
            mock_cache = AsyncMock()
            mock_cache.get.return_value = None
            mock_get_cache.return_value = mock_cache

            mock_service = AsyncMock()
            mock_service.get_location_hierarchy.return_value = [
                {"value": "USA", "label": "United States", "count": 100, "type": "country"}
            ]
            mock_service_class.return_value = mock_service

            # Act
            response = await client.get("/jobs/filters/locations")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["value"] == "USA"
