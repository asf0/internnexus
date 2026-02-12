"""Tests for jobs API endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Job, JobCategory, JobSource


class TestListJobs:
    """Test listing jobs endpoint."""

    def test_list_jobs_basic(self, client: TestClient, sample_jobs: list[Job]):
        """Test basic job listing."""
        response = client.get("/jobs")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert len(data["items"]) > 0

    def test_list_jobs_pagination(self, client: TestClient, sample_jobs: list[Job]):
        """Test job listing with pagination."""
        response = client.get("/jobs?page=1&page_size=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 5
        assert data["page"] == 1
        assert data["page_size"] == 5

    def test_list_jobs_search(self, client: TestClient, sample_jobs: list[Job]):
        """Test searching jobs."""
        response = client.get("/jobs?search=Software")

        assert response.status_code == 200
        data = response.json()
        # Should filter to jobs with "Software" in title, company, or location
        for job in data["items"]:
            assert (
                "software" in job["title"].lower()
                or "software" in job["company"].lower()
                or "software" in job["location"].lower()
            )

    def test_list_jobs_filter_by_company(self, client: TestClient, sample_jobs: list[Job]):
        """Test filtering jobs by company."""
        response = client.get("/jobs?company=Company%200")

        assert response.status_code == 200
        data = response.json()
        for job in data["items"]:
            assert job["company"] == "Company 0"

    def test_list_jobs_filter_by_multiple_companies(
        self, client: TestClient, sample_jobs: list[Job]
    ):
        """Test filtering jobs by multiple companies."""
        response = client.get("/jobs?company=Company%200|Company%201")

        assert response.status_code == 200
        data = response.json()
        for job in data["items"]:
            assert job["company"] in ["Company 0", "Company 1"]

    def test_list_jobs_filter_by_location(self, client: TestClient, sample_jobs: list[Job]):
        """Test filtering jobs by location."""
        response = client.get("/jobs?location=San%20Francisco")

        assert response.status_code == 200
        data = response.json()
        for job in data["items"]:
            assert "san francisco" in job["location"].lower()

    def test_list_jobs_filter_by_category(self, client: TestClient, sample_jobs: list[Job]):
        """Test filtering jobs by category."""
        response = client.get("/jobs?category=software_engineering")

        assert response.status_code == 200
        data = response.json()
        for job in data["items"]:
            assert job["job_category"] == "software_engineering"

    def test_list_jobs_filter_by_visa_sponsored(self, client: TestClient, sample_jobs: list[Job]):
        """Test filtering jobs by visa sponsorship."""
        response = client.get("/jobs?visa_sponsored=true")

        assert response.status_code == 200
        data = response.json()
        for job in data["items"]:
            assert job["visa_sponsored"] is True

    def test_list_jobs_filter_by_f1_friendly(self, client: TestClient, sample_jobs: list[Job]):
        """Test filtering jobs by F1 friendliness."""
        response = client.get("/jobs?f1_friendly=true")

        assert response.status_code == 200
        data = response.json()
        for job in data["items"]:
            assert job["f1_friendly"] is True

    def test_list_jobs_filter_by_job_type_internship(self, client: TestClient, db_session: Session):
        """Test filtering jobs by internship type."""
        # Create a job with "intern" in the title
        intern_job = Job(
            id=uuid4(),
            fingerprint=f"intern-{uuid4()}",
            source=JobSource.greenhouse,
            title="Software Engineering Intern",
            company="Test Co",
            location="Remote",
            apply_url="https://example.com",
            description_text="Internship position",
            is_active=True,
        )
        db_session.add(intern_job)
        db_session.commit()

        response = client.get("/jobs?job_type=internship")

        assert response.status_code == 200
        data = response.json()
        for job in data["items"]:
            assert "intern" in job["title"].lower()

    def test_list_jobs_filter_by_work_mode_remote(self, client: TestClient, db_session: Session):
        """Test filtering jobs by remote work mode."""
        # Create a remote job
        remote_job = Job(
            id=uuid4(),
            fingerprint=f"remote-{uuid4()}",
            source=JobSource.greenhouse,
            title="Remote Developer",
            company="Test Co",
            location="Remote",
            apply_url="https://example.com",
            description_text="Remote position",
            is_active=True,
        )
        db_session.add(remote_job)
        db_session.commit()

        response = client.get("/jobs?work_mode=remote")

        assert response.status_code == 200
        data = response.json()
        for job in data["items"]:
            assert "remote" in job["title"].lower() or "remote" in job["location"].lower()

    def test_list_jobs_filter_by_posted_within(self, client: TestClient, db_session: Session):
        """Test filtering jobs by posted date."""
        # Create a recent job
        recent_job = Job(
            id=uuid4(),
            fingerprint=f"recent-{uuid4()}",
            source=JobSource.greenhouse,
            title="Recent Job",
            company="Test Co",
            location="NYC",
            apply_url="https://example.com",
            description_text="Recent position",
            posted_at=datetime.now(timezone.utc) - timedelta(hours=12),
            is_active=True,
        )
        db_session.add(recent_job)
        db_session.commit()

        response = client.get("/jobs?posted_within=24h")

        assert response.status_code == 200
        data = response.json()
        # Should include only jobs posted within 24 hours
        assert len(data["items"]) >= 1

    def test_list_jobs_with_match_ids(self, client: TestClient, sample_jobs: list[Job]):
        """Test listing jobs with specific match IDs."""
        job_ids = [str(job.id) for job in sample_jobs[:3]]
        match_ids = "|".join(job_ids)

        response = client.get(f"/jobs?match_ids={match_ids}")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        returned_ids = {job["id"] for job in data["items"]}
        assert returned_ids == set(job_ids)

    def test_list_jobs_combined_filters(self, client: TestClient, sample_jobs: list[Job]):
        """Test listing jobs with multiple filters."""
        response = client.get("/jobs?company=Company%200&visa_sponsored=true")

        assert response.status_code == 200
        data = response.json()
        for job in data["items"]:
            assert job["company"] == "Company 0"
            assert job["visa_sponsored"] is True

    def test_list_jobs_invalid_page(self, client: TestClient):
        """Test listing jobs with invalid page number."""
        response = client.get("/jobs?page=0")

        assert response.status_code == 422

    def test_list_jobs_invalid_page_size(self, client: TestClient):
        """Test listing jobs with invalid page size."""
        response = client.get("/jobs?page_size=200")

        assert response.status_code == 422


class TestGetJob:
    """Test getting a single job endpoint."""

    def test_get_job_by_id(self, client: TestClient, sample_job: Job):
        """Test getting a job by ID."""
        response = client.get(f"/jobs/{sample_job.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_job.id)
        assert data["title"] == sample_job.title
        assert data["company"] == sample_job.company

    def test_get_job_not_found(self, client: TestClient):
        """Test getting a non-existent job."""
        response = client.get(f"/jobs/{uuid4()}")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_get_inactive_job(self, client: TestClient, db_session: Session):
        """Test getting an inactive job."""
        inactive_job = Job(
            id=uuid4(),
            fingerprint=f"inactive-{uuid4()}",
            source=JobSource.greenhouse,
            title="Inactive Job",
            company="Test Co",
            location="NYC",
            apply_url="https://example.com",
            description_text="Inactive position",
            is_active=False,
        )
        db_session.add(inactive_job)
        db_session.commit()

        response = client.get(f"/jobs/{inactive_job.id}")

        assert response.status_code == 404


class TestGetFilterOptions:
    """Test filter options endpoints."""

    def test_get_companies(self, client: TestClient, sample_jobs: list[Job]):
        """Test getting list of companies."""
        response = client.get("/jobs/filters/companies")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Should be sorted alphabetically
        assert data == sorted(data)

    def test_get_locations(self, client: TestClient, sample_jobs: list[Job]):
        """Test getting list of locations."""
        response = client.get("/jobs/filters/locations")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should be sorted alphabetically
        assert data == sorted(data)

    def test_get_categories(self, client: TestClient, sample_jobs: list[Job]):
        """Test getting list of categories."""
        response = client.get("/jobs/filters/categories")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should not contain None values
        assert None not in data

    def test_get_companies_only_active(self, client: TestClient, db_session: Session):
        """Test that only active jobs' companies are returned."""
        # Create an inactive job with a unique company
        inactive_job = Job(
            id=uuid4(),
            fingerprint=f"inactive-{uuid4()}",
            source=JobSource.greenhouse,
            title="Inactive",
            company="Inactive Company",
            location="NYC",
            apply_url="https://example.com",
            description_text="Inactive",
            is_active=False,
        )
        db_session.add(inactive_job)
        db_session.commit()

        response = client.get("/jobs/filters/companies")

        assert response.status_code == 200
        data = response.json()
        assert "Inactive Company" not in data


class TestJobNormalization:
    """Test job location normalization."""

    def test_normalize_location_basic(self, client: TestClient):
        """Test basic location normalization."""
        from app.api.jobs import normalize_location

        result = normalize_location("San Francisco, CA")
        assert result is not None
        assert "San Francisco" in result

    def test_normalize_location_remote(self, client: TestClient):
        """Test normalizing remote location."""
        from app.api.jobs import normalize_location

        result = normalize_location("Remote")
        assert result == "Remote"

    def test_normalize_location_empty(self, client: TestClient):
        """Test normalizing empty location."""
        from app.api.jobs import normalize_location

        result = normalize_location("")
        assert result is None

    def test_normalize_location_street_address(self, client: TestClient):
        """Test that street addresses are filtered out."""
        from app.api.jobs import normalize_location

        result = normalize_location("123 Main Street, San Francisco, CA")
        assert result is None

    def test_normalize_location_country_only(self, client: TestClient):
        """Test that country-only locations are filtered out."""
        from app.api.jobs import normalize_location

        result = normalize_location("USA")
        assert result is None


class TestJobTypeExtraction:
    """Test job type extraction from titles."""

    def test_extract_internship(self, client: TestClient):
        """Test extracting internship type."""
        from app.api.jobs import extract_job_type

        assert extract_job_type("Software Engineer Intern") == "internship"
        assert extract_job_type("Summer Internship Program") == "internship"

    def test_extract_full_time(self, client: TestClient):
        """Test extracting full-time type."""
        from app.api.jobs import extract_job_type

        assert extract_job_type("Full-Time Software Engineer") == "full-time"
        assert extract_job_type("Full Time Position") == "full-time"

    def test_extract_part_time(self, client: TestClient):
        """Test extracting part-time type."""
        from app.api.jobs import extract_job_type

        assert extract_job_type("Part-Time Developer") == "part-time"
        assert extract_job_type("Part Time Role") == "part-time"

    def test_extract_no_type(self, client: TestClient):
        """Test extracting from title without job type."""
        from app.api.jobs import extract_job_type

        assert extract_job_type("Software Engineer") is None
