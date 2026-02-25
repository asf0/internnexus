"""Unit tests for auth service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException

from app.services.auth_service import AuthService
from app.services.errors import ConflictError
from app.models import User


class TestAuthService:
    """Test suite for AuthService."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.flush = AsyncMock()
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
    def mock_password_repo(self):
        """Create a mock password history repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def auth_service(self, mock_session, mock_user_repo, mock_account_repo, mock_password_repo):
        """Create an AuthService with mocked dependencies."""
        service = AuthService(mock_session)
        service.user_repo = mock_user_repo
        service.account_repo = mock_account_repo
        service.password_repo = mock_password_repo
        return service

    @pytest.mark.asyncio
    async def test_register_user_success(self, auth_service, mock_user_repo, mock_account_repo):
        """Test successful user registration."""
        # Arrange
        mock_user_repo.get_by_email.return_value = None
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()
        mock_user.email = "test@example.com"
        mock_user.name = "Test User"
        mock_user.password_changed_at = None
        mock_user_repo.create_user.return_value = mock_user
        mock_account_repo.create_credentials_account = AsyncMock()

        # Act
        with patch("app.services.auth_service.create_access_token") as mock_create_token:
            mock_create_token.return_value = "test-token"
            user, token = await auth_service.register_user(
                email="test@example.com", password="SecurePass123!", name="Test User"
            )

        # Assert
        assert user == mock_user
        assert token == "test-token"
        mock_user_repo.create_user.assert_called_once()
        mock_account_repo.create_credentials_account.assert_called_once()
        auth_service.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_user_email_exists_with_oauth(
        self, auth_service, mock_user_repo, mock_account_repo
    ):
        """Test registration when email exists with OAuth provider."""
        # Arrange
        existing_user = MagicMock(spec=User)
        existing_user.id = uuid4()
        mock_user_repo.get_by_email.return_value = existing_user
        mock_account_repo.get_oauth_providers.return_value = ["google"]

        # Act & Assert
        with pytest.raises(ConflictError) as exc_info:
            await auth_service.register_user(
                email="test@example.com", password="SecurePass123!", name="Test User"
            )

        assert exc_info.value.action == "SET_PASSWORD"
        assert "google" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_register_user_email_exists_without_oauth(
        self, auth_service, mock_user_repo, mock_account_repo
    ):
        """Test registration when email exists without OAuth."""
        # Arrange
        existing_user = MagicMock(spec=User)
        existing_user.id = uuid4()
        mock_user_repo.get_by_email.return_value = existing_user
        mock_account_repo.get_oauth_providers.return_value = []

        # Act & Assert
        with pytest.raises(ConflictError) as exc_info:
            await auth_service.register_user(
                email="test@example.com", password="SecurePass123!", name="Test User"
            )

        assert exc_info.value.action == "SIGN_IN"

    @pytest.mark.asyncio
    async def test_login_user_success(self, auth_service, mock_user_repo):
        """Test successful user login."""
        # Arrange
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()
        mock_user.email = "test@example.com"
        mock_user.name = "Test User"
        mock_user.hashed_password = "$argon2id$v=19$m=65536,t=3,p=4$..."
        mock_user.password_changed_at = None
        mock_user_repo.get_by_email.return_value = mock_user

        # Act
        with (
            patch("app.services.auth_service.verify_password") as mock_verify,
            patch("app.services.auth_service.create_access_token") as mock_create_token,
        ):
            mock_verify.return_value = True
            mock_create_token.return_value = "test-token"
            user, token = await auth_service.login_user(
                email="test@example.com", password="SecurePass123!"
            )

        # Assert
        assert user == mock_user
        assert token == "test-token"

    @pytest.mark.asyncio
    async def test_login_user_not_found(self, auth_service, mock_user_repo):
        """Test login with non-existent email."""
        # Arrange
        mock_user_repo.get_by_email.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login_user(email="test@example.com", password="SecurePass123!")

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_login_user_wrong_password(self, auth_service, mock_user_repo):
        """Test login with incorrect password."""
        # Arrange
        mock_user = MagicMock(spec=User)
        mock_user.hashed_password = "$argon2id$..."
        mock_user_repo.get_by_email.return_value = mock_user

        # Act & Assert
        with patch("app.services.auth_service.verify_password") as mock_verify:
            mock_verify.return_value = False
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.login_user(email="test@example.com", password="WrongPass123!")

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_login_user_oauth_account_no_password(
        self, auth_service, mock_user_repo, mock_account_repo
    ):
        """Test login for OAuth user without password."""
        # Arrange
        mock_user = MagicMock(spec=User)
        mock_user.hashed_password = None
        mock_user_repo.get_by_email.return_value = mock_user
        mock_account_repo.get_oauth_providers.return_value = ["github"]

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.login_user(email="test@example.com", password="anypassword")

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["action"] == "USE_OAUTH"

    @pytest.mark.asyncio
    async def test_set_password_success(self, auth_service, mock_account_repo):
        """Test setting password for OAuth user."""
        # Arrange
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()
        mock_user.email = "test@example.com"
        mock_user.hashed_password = None
        mock_user.password_changed_at = None

        # Act
        with (
            patch("app.services.auth_service.get_password_hash") as mock_hash,
            patch("app.services.auth_service.create_access_token") as mock_create_token,
        ):
            mock_hash.return_value = "hashed-password"
            mock_create_token.return_value = "test-token"
            user, token = await auth_service.set_password(mock_user, "NewPass123!")

        # Assert
        assert user.hashed_password == "hashed-password"
        assert token == "test-token"
        assert mock_user.password_changed_at is not None
        auth_service.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_success(self, auth_service, mock_password_repo):
        """Test changing password with correct current password."""
        # Arrange
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()
        mock_user.hashed_password = "old-hashed-password"

        # Act
        with (
            patch("app.services.auth_service.verify_password") as mock_verify,
            patch("app.services.auth_service.get_password_hash") as mock_hash,
        ):
            mock_verify.return_value = True
            mock_hash.return_value = "new-hashed-password"
            await auth_service.change_password(
                user=mock_user, current_password="OldPass123!", new_password="NewPass123!"
            )

        # Assert
        assert mock_user.hashed_password == "new-hashed-password"
        auth_service.session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, auth_service):
        """Test changing password with incorrect current password."""
        # Arrange
        mock_user = MagicMock(spec=User)
        mock_user.hashed_password = "old-hashed-password"

        # Act & Assert
        with patch("app.services.auth_service.verify_password") as mock_verify:
            mock_verify.return_value = False
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.change_password(
                    user=mock_user, current_password="WrongPass123!", new_password="NewPass123!"
                )

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_change_password_same_as_old(self, auth_service):
        """Test changing password to same as current."""
        # Arrange
        mock_user = MagicMock(spec=User)
        mock_user.hashed_password = "hashed-password"

        # Act & Assert
        with patch("app.services.auth_service.verify_password") as mock_verify:
            mock_verify.return_value = True
            with pytest.raises(HTTPException) as exc_info:
                await auth_service.change_password(
                    user=mock_user,
                    current_password="CurrentPass123!",
                    new_password="CurrentPass123!",
                )

        assert exc_info.value.status_code == 400
        assert "same as the current" in exc_info.value.detail["message"]
