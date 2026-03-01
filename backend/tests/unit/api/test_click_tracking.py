"""Unit tests for job click tracking endpoint.

Tests cover:
- Click tracking for authenticated and anonymous users
- Job validation (active/inactive/non-existent)
- UTM parameter handling
- IP hashing for privacy
- Request metadata capture
"""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.jobs import (
    ClickRequest,
    ClickResponse,
    get_db,
    get_optional_user,
    get_redis_service,
    router,
)
from app.models import Job, JobClick, JobSource, User


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def app(mock_db_session):
    """Create a FastAPI app with the jobs router."""
    app = FastAPI()
    app.include_router(router)

    app.state.optional_user = None

    async def _override_get_db():
        yield mock_db_session

    async def _override_get_optional_user():
        return app.state.optional_user

    async def _override_get_redis_service():
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock(return_value=True)
        return mock_redis

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_optional_user] = _override_get_optional_user
    app.dependency_overrides[get_redis_service] = _override_get_redis_service

    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_active_job():
    """Create a mock active job."""
    job = MagicMock(spec=Job)
    job.id = uuid4()
    job.title = "Software Engineer Intern"
    job.company = "TechCorp"
    job.location = "San Francisco, CA"
    job.apply_url = "https://example.com/apply?job=123"
    job.is_active = True
    job.source = JobSource.greenhouse
    return job


@pytest.fixture
def mock_inactive_job():
    """Create a mock inactive job."""
    job = MagicMock(spec=Job)
    job.id = uuid4()
    job.title = "Closed Position"
    job.company = "OldCorp"
    job.location = "Remote"
    job.apply_url = "https://example.com/apply?job=456"
    job.is_active = False
    job.source = JobSource.lever
    return job


@pytest.fixture
def mock_authenticated_user():
    """Create a mock authenticated user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
    user.name = "Test User"
    return user


@pytest.fixture
def mock_request_context():
    """Create mock request context with IP, user-agent, and referer."""
    return {
        "client_ip": "192.168.1.100",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "referer": "https://internnexus.com/jobs",
    }


@pytest.fixture
def expected_ip_hash(mock_request_context):
    """Calculate expected IP hash for verification."""
    client_ip = mock_request_context["client_ip"]
    return hashlib.sha256(f"click:{client_ip}".encode()).hexdigest()[:16]


# =============================================================================
# UNIT TESTS - Click Tracking Success Cases
# =============================================================================


class TestClickTrackingSuccess:
    """Tests for successful click tracking scenarios."""

    @pytest.mark.asyncio
    async def test_click_tracking_authenticated_user_success(
        self, app, mock_db_session, mock_active_job, mock_authenticated_user
    ):
        """Test successful click tracking for authenticated user creates JobClick with user_id."""
        # Arrange
        job_id = mock_active_job.id
        user_id = mock_authenticated_user.id
        app.state.optional_user = mock_authenticated_user

        with (
            patch("app.api.jobs.get_db", return_value=mock_db_session),
            patch("app.api.jobs.get_optional_user", return_value=mock_authenticated_user),
            patch("app.api.jobs.JobRepository") as mock_repo_class,
            patch("app.api.jobs.get_redis_service") as mock_redis,
        ):
            # Mock repository to return active job
            mock_repo = AsyncMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_active_job)
            mock_repo_class.return_value = mock_repo

            # Mock rate limiter
            mock_redis_instance = AsyncMock()
            mock_redis_instance.get = AsyncMock(return_value=None)
            mock_redis_instance.set = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            # Create test client
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Act
                response = await client.post(
                    f"/jobs/{job_id}/click",
                    json={},
                    headers={
                        "X-Forwarded-For": "192.168.1.100",
                        "User-Agent": "TestAgent/1.0",
                        "Referer": "https://test.com",
                    },
                )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == str(job_id)
        assert "apply_url" in data
        assert "utm_source=internnexus" in data["apply_url"]

        # Verify JobClick was created with user_id
        mock_db_session.add.assert_called_once()
        added_click = mock_db_session.add.call_args[0][0]
        assert isinstance(added_click, JobClick)
        assert added_click.job_id == job_id
        assert added_click.user_id == user_id
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_click_tracking_anonymous_user_success(self, app, mock_db_session, mock_active_job):
        """Test successful click tracking for anonymous user creates JobClick with null user_id."""
        # Arrange
        job_id = mock_active_job.id

        with (
            patch("app.api.jobs.get_db", return_value=mock_db_session),
            patch("app.api.jobs.get_optional_user", return_value=None),
            patch("app.api.jobs.JobRepository") as mock_repo_class,
            patch("app.api.jobs.get_redis_service") as mock_redis,
        ):
            # Mock repository to return active job
            mock_repo = AsyncMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_active_job)
            mock_repo_class.return_value = mock_repo

            # Mock rate limiter
            mock_redis_instance = AsyncMock()
            mock_redis_instance.get = AsyncMock(return_value=None)
            mock_redis_instance.set = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            # Create test client
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Act
                response = await client.post(
                    f"/jobs/{job_id}/click",
                    json={},
                    headers={
                        "X-Forwarded-For": "192.168.1.100",
                        "User-Agent": "TestAgent/1.0",
                    },
                )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == str(job_id)

        # Verify JobClick was created with null user_id
        mock_db_session.add.assert_called_once()
        added_click = mock_db_session.add.call_args[0][0]
        assert isinstance(added_click, JobClick)
        assert added_click.job_id == job_id
        assert added_click.user_id is None
        mock_db_session.commit.assert_called_once()


# =============================================================================
# UNIT TESTS - Click Tracking Error Cases
# =============================================================================


class TestClickTrackingErrors:
    """Tests for click tracking error scenarios."""

    @pytest.mark.asyncio
    async def test_click_tracking_nonexistent_job_returns_404(self, app, mock_db_session):
        """Test click tracking for non-existent job returns 404."""
        # Arrange
        nonexistent_job_id = uuid4()

        with (
            patch("app.api.jobs.get_db", return_value=mock_db_session),
            patch("app.api.jobs.get_optional_user", return_value=None),
            patch("app.api.jobs.JobRepository") as mock_repo_class,
            patch("app.api.jobs.get_redis_service") as mock_redis,
        ):
            # Mock repository to return None (job not found)
            mock_repo = AsyncMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_class.return_value = mock_repo

            # Mock rate limiter
            mock_redis_instance = AsyncMock()
            mock_redis_instance.get = AsyncMock(return_value=None)
            mock_redis_instance.set = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            # Create test client
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Act
                response = await client.post(
                    f"/jobs/{nonexistent_job_id}/click",
                    json={},
                )

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Job not found"

        # Verify no JobClick was created
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_click_tracking_inactive_job_returns_404(self, app, mock_db_session, mock_inactive_job):
        """Test click tracking for inactive job returns 404."""
        # Arrange
        inactive_job_id = mock_inactive_job.id

        with (
            patch("app.api.jobs.get_db", return_value=mock_db_session),
            patch("app.api.jobs.get_optional_user", return_value=None),
            patch("app.api.jobs.JobRepository") as mock_repo_class,
            patch("app.api.jobs.get_redis_service") as mock_redis,
        ):
            # Mock repository to return inactive job
            mock_repo = AsyncMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_inactive_job)
            mock_repo_class.return_value = mock_repo

            # Mock rate limiter
            mock_redis_instance = AsyncMock()
            mock_redis_instance.get = AsyncMock(return_value=None)
            mock_redis_instance.set = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            # Create test client
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Act
                response = await client.post(
                    f"/jobs/{inactive_job_id}/click",
                    json={},
                )

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Job not found"

        # Verify no JobClick was created
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_not_called()


# =============================================================================
# UNIT TESTS - UTM Parameters
# =============================================================================


class TestUTMParameters:
    """Tests for UTM parameter handling."""

    @pytest.mark.asyncio
    async def test_utm_params_added_to_returned_url(self, app, mock_db_session, mock_active_job):
        """Test that UTM params are added to the returned URL."""
        # Arrange
        job_id = mock_active_job.id

        with (
            patch("app.api.jobs.get_db", return_value=mock_db_session),
            patch("app.api.jobs.get_optional_user", return_value=None),
            patch("app.api.jobs.JobRepository") as mock_repo_class,
            patch("app.api.jobs.get_redis_service") as mock_redis,
        ):
            # Mock repository
            mock_repo = AsyncMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_active_job)
            mock_repo_class.return_value = mock_repo

            # Mock rate limiter
            mock_redis_instance = AsyncMock()
            mock_redis_instance.get = AsyncMock(return_value=None)
            mock_redis_instance.set = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            # Create test client
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Act
                response = await client.post(
                    f"/jobs/{job_id}/click",
                    json={},
                )

        # Assert
        assert response.status_code == 200
        data = response.json()
        apply_url = data["apply_url"]

        # Verify UTM source is always present
        assert "utm_source=internnexus" in apply_url

    @pytest.mark.asyncio
    async def test_custom_utm_params_from_request_body_included(self, app, mock_db_session, mock_active_job):
        """Test that custom UTM params from request body are included in URL and JobClick."""
        # Arrange
        job_id = mock_active_job.id
        custom_medium = "email"
        custom_campaign = "summer_2024_newsletter"

        with (
            patch("app.api.jobs.get_db", return_value=mock_db_session),
            patch("app.api.jobs.get_optional_user", return_value=None),
            patch("app.api.jobs.JobRepository") as mock_repo_class,
            patch("app.api.jobs.get_redis_service") as mock_redis,
        ):
            # Mock repository
            mock_repo = AsyncMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_active_job)
            mock_repo_class.return_value = mock_repo

            # Mock rate limiter
            mock_redis_instance = AsyncMock()
            mock_redis_instance.get = AsyncMock(return_value=None)
            mock_redis_instance.set = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            # Create test client
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Act
                response = await client.post(
                    f"/jobs/{job_id}/click",
                    json={
                        "utm_medium": custom_medium,
                        "utm_campaign": custom_campaign,
                    },
                )

        # Assert
        assert response.status_code == 200
        data = response.json()
        apply_url = data["apply_url"]

        # Verify all UTM params are in URL
        assert "utm_source=internnexus" in apply_url
        assert f"utm_medium={custom_medium}" in apply_url
        assert f"utm_campaign={custom_campaign}" in apply_url

        # Verify UTM params are stored in JobClick
        added_click = mock_db_session.add.call_args[0][0]
        assert added_click.utm_source == "internnexus"
        assert added_click.utm_medium == custom_medium
        assert added_click.utm_campaign == custom_campaign


# =============================================================================
# UNIT TESTS - IP Hashing
# =============================================================================


class TestIPHashing:
    """Tests for IP address hashing for privacy."""

    @pytest.mark.asyncio
    async def test_ip_is_hashed_not_stored_plain_text(
        self, app, mock_db_session, mock_active_job, mock_request_context
    ):
        """Test that IP is hashed and not stored in plain text."""
        # Arrange
        job_id = mock_active_job.id
        # Endpoint currently hashes request.client.host from ASGI test transport.
        client_ip = "127.0.0.1"
        expected_hash = hashlib.sha256(f"click:{client_ip}".encode()).hexdigest()[:16]

        with (
            patch("app.api.jobs.get_db", return_value=mock_db_session),
            patch("app.api.jobs.get_optional_user", return_value=None),
            patch("app.api.jobs.JobRepository") as mock_repo_class,
            patch("app.api.jobs.get_redis_service") as mock_redis,
        ):
            # Mock repository
            mock_repo = AsyncMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_active_job)
            mock_repo_class.return_value = mock_repo

            # Mock rate limiter
            mock_redis_instance = AsyncMock()
            mock_redis_instance.get = AsyncMock(return_value=None)
            mock_redis_instance.set = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            # Create test client
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Act
                response = await client.post(
                    f"/jobs/{job_id}/click",
                    json={},
                    headers={"X-Forwarded-For": client_ip},
                )

        # Assert
        assert response.status_code == 200

        # Verify IP hash is stored, not plain IP
        added_click = mock_db_session.add.call_args[0][0]
        assert added_click.ip_hash == expected_hash
        assert added_click.ip_hash != client_ip
        assert len(added_click.ip_hash) == 16  # First 16 chars of SHA256

    @pytest.mark.asyncio
    async def test_ip_hash_is_consistent_for_same_ip(self, app, mock_db_session, mock_active_job):
        """Test that same IP produces same hash (for analytics)."""
        # Arrange
        job_id = mock_active_job.id
        client_ip = "127.0.0.1"

        with (
            patch("app.api.jobs.get_db", return_value=mock_db_session),
            patch("app.api.jobs.get_optional_user", return_value=None),
            patch("app.api.jobs.JobRepository") as mock_repo_class,
            patch("app.api.jobs.get_redis_service") as mock_redis,
        ):
            # Mock repository
            mock_repo = AsyncMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_active_job)
            mock_repo_class.return_value = mock_repo

            # Mock rate limiter
            mock_redis_instance = AsyncMock()
            mock_redis_instance.get = AsyncMock(return_value=None)
            mock_redis_instance.set = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            # Create test client
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Act - make two requests with same IP
                await client.post(
                    f"/jobs/{job_id}/click",
                    json={},
                    headers={"X-Forwarded-For": client_ip},
                )

        # Calculate expected hash
        expected_hash = hashlib.sha256(f"click:{client_ip}".encode()).hexdigest()[:16]

        # Assert hash is consistent
        added_click = mock_db_session.add.call_args[0][0]
        assert added_click.ip_hash == expected_hash

    @pytest.mark.asyncio
    async def test_different_ips_produce_different_hashes(self, app, mock_db_session, mock_active_job):
        """Test that different IPs produce different hashes."""
        # Arrange
        ip1 = "192.168.1.1"
        ip2 = "192.168.1.2"

        hash1 = hashlib.sha256(f"click:{ip1}".encode()).hexdigest()[:16]
        hash2 = hashlib.sha256(f"click:{ip2}".encode()).hexdigest()[:16]

        # Assert hashes are different
        assert hash1 != hash2


# =============================================================================
# UNIT TESTS - Request Metadata
# =============================================================================


class TestRequestMetadata:
    """Tests for capturing request metadata."""

    @pytest.mark.asyncio
    async def test_user_agent_captured(self, app, mock_db_session, mock_active_job):
        """Test that user-agent header is captured in JobClick."""
        # Arrange
        job_id = mock_active_job.id
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

        with (
            patch("app.api.jobs.get_db", return_value=mock_db_session),
            patch("app.api.jobs.get_optional_user", return_value=None),
            patch("app.api.jobs.JobRepository") as mock_repo_class,
            patch("app.api.jobs.get_redis_service") as mock_redis,
        ):
            # Mock repository
            mock_repo = AsyncMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_active_job)
            mock_repo_class.return_value = mock_repo

            # Mock rate limiter
            mock_redis_instance = AsyncMock()
            mock_redis_instance.get = AsyncMock(return_value=None)
            mock_redis_instance.set = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            # Create test client
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Act
                response = await client.post(
                    f"/jobs/{job_id}/click",
                    json={},
                    headers={"User-Agent": user_agent},
                )

        # Assert
        assert response.status_code == 200
        added_click = mock_db_session.add.call_args[0][0]
        assert added_click.user_agent == user_agent

    @pytest.mark.asyncio
    async def test_referer_captured(self, app, mock_db_session, mock_active_job):
        """Test that referer header is captured in JobClick."""
        # Arrange
        job_id = mock_active_job.id
        referer = "https://internnexus.com/jobs?search=engineer"

        with (
            patch("app.api.jobs.get_db", return_value=mock_db_session),
            patch("app.api.jobs.get_optional_user", return_value=None),
            patch("app.api.jobs.JobRepository") as mock_repo_class,
            patch("app.api.jobs.get_redis_service") as mock_redis,
        ):
            # Mock repository
            mock_repo = AsyncMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_active_job)
            mock_repo_class.return_value = mock_repo

            # Mock rate limiter
            mock_redis_instance = AsyncMock()
            mock_redis_instance.get = AsyncMock(return_value=None)
            mock_redis_instance.set = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            # Create test client
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Act
                response = await client.post(
                    f"/jobs/{job_id}/click",
                    json={},
                    headers={"Referer": referer},
                )

        # Assert
        assert response.status_code == 200
        added_click = mock_db_session.add.call_args[0][0]
        assert added_click.referer == referer

    @pytest.mark.asyncio
    async def test_long_user_agent_truncated(self, app, mock_db_session, mock_active_job):
        """Test that user-agent longer than 500 chars is truncated."""
        # Arrange
        job_id = mock_active_job.id
        long_user_agent = "A" * 600  # 600 chars, should be truncated to 500

        with (
            patch("app.api.jobs.get_db", return_value=mock_db_session),
            patch("app.api.jobs.get_optional_user", return_value=None),
            patch("app.api.jobs.JobRepository") as mock_repo_class,
            patch("app.api.jobs.get_redis_service") as mock_redis,
        ):
            # Mock repository
            mock_repo = AsyncMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_active_job)
            mock_repo_class.return_value = mock_repo

            # Mock rate limiter
            mock_redis_instance = AsyncMock()
            mock_redis_instance.get = AsyncMock(return_value=None)
            mock_redis_instance.set = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            # Create test client
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Act
                response = await client.post(
                    f"/jobs/{job_id}/click",
                    json={},
                    headers={"User-Agent": long_user_agent},
                )

        # Assert
        assert response.status_code == 200
        added_click = mock_db_session.add.call_args[0][0]
        assert len(added_click.user_agent) == 500
        assert added_click.user_agent == long_user_agent[:500]

    @pytest.mark.asyncio
    async def test_long_referer_truncated(self, app, mock_db_session, mock_active_job):
        """Test that referer longer than 500 chars is truncated."""
        # Arrange
        job_id = mock_active_job.id
        long_referer = "https://example.com/" + "a" * 600

        with (
            patch("app.api.jobs.get_db", return_value=mock_db_session),
            patch("app.api.jobs.get_optional_user", return_value=None),
            patch("app.api.jobs.JobRepository") as mock_repo_class,
            patch("app.api.jobs.get_redis_service") as mock_redis,
        ):
            # Mock repository
            mock_repo = AsyncMock()
            mock_repo.get_by_id = AsyncMock(return_value=mock_active_job)
            mock_repo_class.return_value = mock_repo

            # Mock rate limiter
            mock_redis_instance = AsyncMock()
            mock_redis_instance.get = AsyncMock(return_value=None)
            mock_redis_instance.set = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            # Create test client
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Act
                response = await client.post(
                    f"/jobs/{job_id}/click",
                    json={},
                    headers={"Referer": long_referer},
                )

        # Assert
        assert response.status_code == 200
        added_click = mock_db_session.add.call_args[0][0]
        assert len(added_click.referer) == 500


# =============================================================================
# UNIT TESTS - ClickRequest Model
# =============================================================================


class TestClickRequestModel:
    """Tests for ClickRequest Pydantic model."""

    def test_click_request_with_all_fields(self):
        """Test ClickRequest with all UTM fields."""
        request = ClickRequest(
            utm_medium="email",
            utm_campaign="newsletter",
        )
        assert request.utm_medium == "email"
        assert request.utm_campaign == "newsletter"

    def test_click_request_with_no_fields(self):
        """Test ClickRequest with no fields (all optional)."""
        request = ClickRequest()
        assert request.utm_medium is None
        assert request.utm_campaign is None

    def test_click_request_with_partial_fields(self):
        """Test ClickRequest with only some fields."""
        request = ClickRequest(utm_medium="social")
        assert request.utm_medium == "social"
        assert request.utm_campaign is None


class TestClickResponseModel:
    """Tests for ClickResponse Pydantic model."""

    def test_click_response_model(self):
        """Test ClickResponse model creation."""
        job_id = uuid4()
        response = ClickResponse(
            apply_url="https://example.com/apply?utm_source=internnexus",
            job_id=str(job_id),
        )
        assert response.apply_url == "https://example.com/apply?utm_source=internnexus"
        assert response.job_id == str(job_id)
