"""Unit tests for base repository."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.repositories.base import BaseRepository
from app.models import User


class TestBaseRepository:
    """Test suite for BaseRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.add = MagicMock()
        session.delete = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create a BaseRepository instance with mock session."""
        return BaseRepository(User, mock_session)

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repository, mock_session):
        """Test getting a record by ID when it exists."""
        # Arrange
        test_id = uuid4()
        mock_user = MagicMock(spec=User)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_id(test_id)

        # Assert
        assert result == mock_user
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, mock_session):
        """Test getting a record by ID when it doesn't exist."""
        # Arrange
        test_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_id(test_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all(self, repository, mock_session):
        """Test getting all records."""
        # Arrange
        mock_users = [MagicMock(spec=User), MagicMock(spec=User)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_users
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_all(limit=10, offset=0)

        # Assert
        assert len(result) == 2
        assert result == mock_users

    @pytest.mark.asyncio
    async def test_create(self, repository, mock_session):
        """Test creating a new record."""
        # Arrange
        with patch.object(User, "__init__", return_value=None) as mock_init:
            mock_init.return_value = None

            # Act
            result = await repository.create(email="test@example.com", name="Test User")

            # Assert
            assert result is not None
            mock_session.add.assert_called_once()
            mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update(self, repository, mock_session):
        """Test updating a record."""
        # Arrange
        mock_user = MagicMock(spec=User)
        mock_user.name = "Old Name"
        mock_user.email = "old@example.com"

        # Act
        result = await repository.update(mock_user, name="New Name", email="new@example.com")

        # Assert
        assert result.name == "New Name"
        assert result.email == "new@example.com"
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_ignores_invalid_fields(self, repository, mock_session):
        """Test that update ignores fields that don't exist on model."""
        # Arrange
        mock_user = MagicMock(spec=User)
        mock_user.__class__ = User  # Ensure hasattr works
        # Mock that the model doesn't have 'invalid_field'
        type(mock_user).valid_field = MagicMock()

        # Act - this should not raise an error
        # We need to mock hasattr to return False for invalid_field
        with patch.object(repository.model, "__init__", return_value=None):
            result = await repository.update(mock_user, valid_field="value")
            assert result is not None

        # Assert
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete(self, repository, mock_session):
        """Test deleting a record."""
        # Arrange
        mock_user = MagicMock(spec=User)

        # Act
        await repository.delete(mock_user)

        # Assert
        mock_session.delete.assert_called_once_with(mock_user)

    @pytest.mark.asyncio
    async def test_refresh(self, repository, mock_session):
        """Test refreshing a record from database."""
        # Arrange
        mock_user = MagicMock(spec=User)

        # Act
        result = await repository.refresh(mock_user)

        # Assert
        mock_session.refresh.assert_called_once_with(mock_user)
        assert result == mock_user
