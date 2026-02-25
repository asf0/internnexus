"""E2E tests for user workflows."""

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4


@pytest.mark.e2e
class TestUserRegistrationFlow:
    """E2E tests for user registration workflow."""

    @pytest.mark.asyncio
    async def test_complete_registration_flow(self, client):
        """Test complete user registration flow."""
        # Arrange - Registration data
        register_data = {
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "name": "New User",
        }

        # Act - Register
        with patch("app.api.auth.get_auth_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_user = MagicMock()
            mock_user.id = uuid4()
            mock_user.email = "newuser@example.com"
            mock_user.name = "New User"
            mock_service.register_user.return_value = (mock_user, "access-token")
            mock_get_service.return_value = mock_service

            response = await client.post("/auth/register", json=register_data)

        # Assert - Registration successful
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "newuser@example.com"

    @pytest.mark.asyncio
    async def test_registration_to_login_flow(self, client):
        """Test registration followed by login."""
        # Arrange - First register
        register_data = {
            "email": "test@example.com",
            "password": "SecurePass123!",
            "name": "Test User",
        }

        with patch("app.api.auth.get_auth_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_user = MagicMock()
            mock_user.id = uuid4()
            mock_user.email = "test@example.com"
            mock_user.name = "Test User"
            mock_user.hashed_password = "$argon2id$..."
            mock_user.password_changed_at = None
            mock_service.register_user.return_value = (mock_user, "register-token")
            mock_get_service.return_value = mock_service

            # Register
            response = await client.post("/auth/register", json=register_data)
            assert response.status_code == 200

        # Now login with same credentials
        login_data = {"email": "test@example.com", "password": "SecurePass123!"}

        with patch("app.api.auth.get_auth_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.login_user.return_value = (mock_user, "login-token")
            mock_get_service.return_value = mock_service

            response = await client.post("/auth/login", json=login_data)

        # Assert - Login successful
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data


@pytest.mark.e2e
class TestOAuthFlow:
    """E2E tests for OAuth authentication flow."""

    @pytest.mark.asyncio
    async def test_google_oauth_flow(self, client):
        """Test complete Google OAuth flow."""
        # Arrange - OAuth callback data
        oauth_data = {
            "provider": "google",
            "provider_account_id": "google-user-123",
            "email": "googleuser@gmail.com",
            "name": "Google User",
            "image": "https://google.com/image.jpg",
            "access_token": "google-oauth-token",
            "refresh_token": "google-refresh-token",
        }

        # Act
        with (
            patch("app.api.auth.verify_oauth_token") as mock_verify,
            patch("app.api.auth.get_auth_service") as mock_get_service,
        ):
            mock_verify.return_value = MagicMock(
                provider_account_id="google-user-123",
                email="googleuser@gmail.com",
                name="Google User",
                picture="https://google.com/image.jpg",
            )

            mock_service = AsyncMock()
            mock_user = MagicMock()
            mock_user.id = uuid4()
            mock_user.email = "googleuser@gmail.com"
            mock_user.name = "Google User"
            mock_service.handle_oauth_callback.return_value = (mock_user, "oauth-token")
            mock_get_service.return_value = mock_service

            response = await client.post("/auth/oauth/callback", json=oauth_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "oauth-token"


@pytest.mark.e2e
class TestJobSearchWorkflow:
    """E2E tests for job search workflow."""

    @pytest.mark.asyncio
    async def test_search_and_filter_workflow(self, client):
        """Test searching jobs and applying filters."""
        # Arrange - First get list of jobs
        from datetime import datetime, timezone
        from uuid import uuid4
        from app.api.schemas import JobListResponse, JobResponse

        with patch("app.api.jobs.get_job_search_service") as mock_get_service:
            mock_service = AsyncMock()

            jobs = [
                JobResponse(
                    id=uuid4(),
                    source="greenhouse",
                    title="Software Engineer",
                    company="Google",
                    location="Mountain View, CA",
                    city="Mountain View",
                    state="CA",
                    country="USA",
                    apply_url="https://google.com/apply",
                    description_text="Build things",
                    job_category="software_engineering",
                    job_type="internship",
                    work_mode="hybrid",
                    posted_at=datetime.now(timezone.utc),
                    is_active=True,
                ),
                JobResponse(
                    id=uuid4(),
                    source="lever",
                    title="Data Scientist",
                    company="Microsoft",
                    location="Redmond, WA",
                    city="Redmond",
                    state="WA",
                    country="USA",
                    apply_url="https://microsoft.com/apply",
                    description_text="Analyze data",
                    job_category="data_science_ai",
                    job_type="full_time",
                    work_mode="remote",
                    posted_at=datetime.now(timezone.utc),
                    is_active=True,
                ),
            ]

            mock_service.search.return_value = JobListResponse(
                items=jobs, total=2, page=1, page_size=20
            )
            mock_get_service.return_value = mock_service

            # Act - Get jobs
            response = await client.get("/jobs")

        # Assert - Got jobs
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

        # Act - Filter by company
        with patch("app.api.jobs.get_job_search_service") as mock_get_service:
            mock_service = AsyncMock()
            mock_service.search.return_value = JobListResponse(
                items=[jobs[0]], total=1, page=1, page_size=20
            )
            mock_get_service.return_value = mock_service

            response = await client.get("/jobs?company=Google")

        # Assert - Filtered correctly
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    @pytest.mark.asyncio
    async def test_job_detail_viewing(self, client):
        """Test viewing job details."""
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
            mock_job.id = uuid4()
            mock_job.source = "greenhouse"
            mock_job.title = "Full Stack Developer"
            mock_job.company = "StartupCo"
            mock_job.location = "San Francisco, CA"
            mock_job.city = "San Francisco"
            mock_job.state = "CA"
            mock_job.country = "USA"
            mock_job.apply_url = "https://startup.co/apply"
            mock_job.description_text = "Join our team!"
            mock_job.job_category = None
            mock_job.job_type = "internship"
            mock_job.work_mode = "hybrid"
            mock_job.posted_at = None
            mock_job.is_active = True
            mock_repo.get_by_id.return_value = mock_job
            mock_repo_class.return_value = mock_repo

            # Act
            response = await client.get(f"/jobs/{job_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Full Stack Developer"
        assert data["company"] == "StartupCo"


@pytest.mark.e2e
class TestUserProfileWorkflow:
    """E2E tests for user profile management workflow."""

    @pytest.mark.asyncio
    async def test_profile_update_workflow(self, client):
        """Test updating user profile."""
        # Arrange
        from datetime import datetime, timezone
        from uuid import uuid4

        update_data = {
            "name": "Updated Name",
            "bio": "Software Developer",
            "location": "San Francisco",
            "job_title": "Engineer",
            "skills": ["Python", "JavaScript"],
        }

        # Act
        with (
            patch("app.api.users.get_current_user") as mock_get_user,
            patch("app.api.users.get_user_service") as mock_get_service,
        ):
            mock_user = MagicMock()
            mock_user.id = uuid4()
            mock_user.email = "test@example.com"
            mock_user.name = "Updated Name"
            mock_user.image = None
            mock_user.created_at = datetime.now(timezone.utc)
            mock_user.bio = "Software Developer"
            mock_user.phone = None
            mock_user.location = "San Francisco"
            mock_user.job_title = "Engineer"
            mock_user.company = None
            mock_user.industry = None
            mock_user.skills = '["Python", "JavaScript"]'
            mock_user.linkedin_url = None
            mock_user.portfolio_url = None
            mock_user.preferred_locations = None
            mock_user.hashed_password = None

            mock_get_user.return_value = mock_user

            mock_service = AsyncMock()
            mock_service.update_profile.return_value = mock_user
            mock_service.parse_user_profile = Mock(
                return_value={
                    "id": str(mock_user.id),
                    "email": mock_user.email,
                    "name": mock_user.name,
                    "image": mock_user.image,
                    "created_at": mock_user.created_at,
                    "bio": mock_user.bio,
                    "phone": mock_user.phone,
                    "location": mock_user.location,
                    "job_title": mock_user.job_title,
                    "company": mock_user.company,
                    "industry": mock_user.industry,
                    "skills": ["Python", "JavaScript"],
                    "linkedin_url": mock_user.linkedin_url,
                    "portfolio_url": mock_user.portfolio_url,
                    "preferred_locations": [],
                    "has_password": False,
                }
            )
            mock_get_service.return_value = mock_service

            response = await client.put("/users/me", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["bio"] == "Software Developer"
        assert data["skills"] == ["Python", "JavaScript"]

    @pytest.mark.asyncio
    async def test_password_change_workflow(self, client):
        """Test changing password."""
        # Arrange
        from uuid import uuid4

        password_data = {"current_password": "OldPass123!", "new_password": "NewSecurePass123!"}

        # Act
        with (
            patch("app.api.users.get_current_user") as mock_get_user,
            patch("app.api.users.get_auth_service") as mock_get_service,
        ):
            mock_user = MagicMock()
            mock_user.id = uuid4()
            mock_user.email = "test@example.com"
            mock_user.hashed_password = "old-hash"
            mock_get_user.return_value = mock_user

            mock_service = AsyncMock()
            mock_get_service.return_value = mock_service

            response = await client.put("/users/me/password", json=password_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "updated successfully" in data["message"]
