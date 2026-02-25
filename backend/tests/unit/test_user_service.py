"""Unit tests for user service."""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.services.user_service import UserService
from app.models import User


class TestUserService:
    """Test suite for UserService."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def mock_user_repo(self):
        """Create a mock user repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_account_repo(self):
        """Create a mock account repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def user_service(self, mock_session, mock_user_repo, mock_account_repo):
        """Create a UserService with mocked dependencies."""
        service = UserService(mock_session)
        service.user_repo = mock_user_repo
        service.account_repo = mock_account_repo
        return service

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = MagicMock(spec=User)
        user.id = uuid4()
        user.email = "test@example.com"
        user.name = "Test User"
        user.image = None
        user.created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        user.bio = None
        user.phone = None
        user.location = None
        user.job_title = None
        user.company = None
        user.industry = None
        user.skills = None
        user.linkedin_url = None
        user.portfolio_url = None
        user.preferred_locations = None
        user.hashed_password = None
        return user

    def test_parse_user_profile_with_null_fields(self, user_service, mock_user):
        """Test parsing user profile with null JSON fields."""
        # Act
        profile = user_service.parse_user_profile(mock_user)

        # Assert
        assert profile["id"] == str(mock_user.id)
        assert profile["email"] == mock_user.email
        assert profile["skills"] == []
        assert profile["preferred_locations"] == []
        assert profile["has_password"] is False

    def test_parse_user_profile_with_skills(self, user_service, mock_user):
        """Test parsing user profile with skills."""
        # Arrange
        mock_user.skills = json.dumps(["Python", "JavaScript"])
        mock_user.preferred_locations = json.dumps(["New York", "San Francisco"])
        mock_user.hashed_password = "some-hash"

        # Act
        profile = user_service.parse_user_profile(mock_user)

        # Assert
        assert profile["skills"] == ["Python", "JavaScript"]
        assert profile["preferred_locations"] == ["New York", "San Francisco"]
        assert profile["has_password"] is True

    @pytest.mark.asyncio
    async def test_update_profile_single_field(self, user_service, mock_user_repo, mock_user):
        """Test updating a single profile field."""
        # Arrange
        mock_user_repo.refresh = AsyncMock(return_value=mock_user)
        data = {"name": "New Name"}

        # Act
        result = await user_service.update_profile(mock_user, data)

        # Assert
        assert result.name == "New Name"
        user_service.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_profile_multiple_fields(self, user_service, mock_user_repo, mock_user):
        """Test updating multiple profile fields."""
        # Arrange
        mock_user_repo.refresh = AsyncMock(return_value=mock_user)
        data = {
            "name": "New Name",
            "bio": "New bio",
            "location": "New York",
            "job_title": "Software Engineer",
        }

        # Act
        result = await user_service.update_profile(mock_user, data)

        # Assert
        assert result.name == "New Name"
        assert result.bio == "New bio"
        assert result.location == "New York"
        assert result.job_title == "Software Engineer"

    @pytest.mark.asyncio
    async def test_update_profile_skills(self, user_service, mock_user_repo, mock_user):
        """Test updating skills as JSON."""
        # Arrange
        mock_user_repo.refresh = AsyncMock(return_value=mock_user)
        data = {"skills": ["Python", "JavaScript", "Go"]}

        # Act
        result = await user_service.update_profile(mock_user, data)

        # Assert
        assert result.skills == json.dumps(["Python", "JavaScript", "Go"])

    @pytest.mark.asyncio
    async def test_update_profile_empty_skills(self, user_service, mock_user_repo, mock_user):
        """Test updating with empty skills."""
        # Arrange
        mock_user_repo.refresh = AsyncMock(return_value=mock_user)
        data = {"skills": []}

        # Act
        result = await user_service.update_profile(mock_user, data)

        # Assert
        assert result.skills is None

    @pytest.mark.asyncio
    async def test_update_profile_ignores_none_values(
        self, user_service, mock_user_repo, mock_user
    ):
        """Test that None values don't overwrite existing data."""
        # Arrange
        mock_user_repo.refresh = AsyncMock(return_value=mock_user)
        mock_user.name = "Existing Name"
        data = {"name": None, "bio": "New bio"}

        # Act
        result = await user_service.update_profile(mock_user, data)

        # Assert
        assert result.name == "Existing Name"  # Should not change
        assert result.bio == "New bio"  # Should update

    @pytest.mark.asyncio
    async def test_delete_account(self, user_service, mock_session, mock_account_repo, mock_user):
        """Test soft deleting user account."""
        # Arrange
        mock_user.name = "Test User"
        mock_user.email = "test@example.com"
        mock_account_repo.get_by_user = AsyncMock(return_value=[])

        # Act
        await user_service.delete_account(mock_user)

        # Assert
        assert mock_user.is_deleted is True
        assert mock_user.deleted_at is not None
        assert mock_user.name is None
        assert "@deleted.invalid" in mock_user.email
        assert mock_user.phone is None
        assert mock_user.bio is None
        assert mock_user.hashed_password is None
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_account_clears_personal_data(
        self, user_service, mock_session, mock_account_repo, mock_user
    ):
        """Test that deletion clears all personal data."""
        # Arrange
        mock_user.name = "John Doe"
        mock_user.email = "john@example.com"
        mock_user.phone = "+1234567890"
        mock_user.location = "New York"
        mock_user.bio = "Software Engineer"
        mock_user.image = "https://example.com/image.jpg"
        mock_user.job_title = "Developer"
        mock_user.company = "TechCorp"
        mock_user.industry = "Technology"
        mock_user.linkedin_url = "https://linkedin.com/in/john"
        mock_user.portfolio_url = "https://johndoe.com"
        mock_user.hashed_password = "password-hash"

        # Act
        await user_service.delete_account(mock_user)

        # Assert
        assert mock_user.name is None
        assert mock_user.phone is None
        assert mock_user.location is None
        assert mock_user.bio is None
        assert mock_user.image is None
        assert mock_user.job_title is None
        assert mock_user.company is None
        assert mock_user.industry is None
        assert mock_user.linkedin_url is None
        assert mock_user.portfolio_url is None
        assert mock_user.hashed_password is None
