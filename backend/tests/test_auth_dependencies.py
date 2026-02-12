"""Tests for authentication dependencies."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_optional_user
from app.auth.jwt import create_access_token
from app.models import User


class TestGetCurrentUser:
    """Test get_current_user dependency."""

    def test_get_current_user_with_valid_token(self, db_session: Session, sample_user: User):
        """Test getting current user with valid token."""
        token = create_access_token(data={"sub": str(sample_user.id), "email": sample_user.email})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        user = get_current_user(credentials, db_session)

        assert user is not None
        assert user.id == sample_user.id
        assert user.email == sample_user.email

    def test_get_current_user_with_no_credentials(self, db_session: Session):
        """Test getting current user with no credentials."""
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(None, db_session)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Authentication required" in str(exc_info.value.detail)

    def test_get_current_user_with_invalid_token(self, db_session: Session):
        """Test getting current user with invalid token."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid.token.here"
        )

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials, db_session)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid or expired token" in str(exc_info.value.detail)

    def test_get_current_user_with_nonexistent_user(self, db_session: Session):
        """Test getting current user when user doesn't exist."""
        nonexistent_id = uuid4()
        token = create_access_token(
            data={"sub": str(nonexistent_id), "email": "nonexistent@example.com"}
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials, db_session)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "User not found" in str(exc_info.value.detail)

    def test_get_current_user_with_expired_token(self, db_session: Session, sample_user: User):
        """Test getting current user with expired token."""
        from datetime import timedelta

        # Create an expired token
        token = create_access_token(
            data={"sub": str(sample_user.id), "email": sample_user.email},
            expires_delta=timedelta(seconds=-1),  # Already expired
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials, db_session)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetOptionalUser:
    """Test get_optional_user dependency."""

    def test_get_optional_user_with_valid_token(self, db_session: Session, sample_user: User):
        """Test getting optional user with valid token."""
        token = create_access_token(data={"sub": str(sample_user.id), "email": sample_user.email})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        user = get_optional_user(credentials, db_session)

        assert user is not None
        assert user.id == sample_user.id

    def test_get_optional_user_with_no_credentials(self, db_session: Session):
        """Test getting optional user with no credentials."""
        user = get_optional_user(None, db_session)

        assert user is None

    def test_get_optional_user_with_invalid_token(self, db_session: Session):
        """Test getting optional user with invalid token."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid.token.here"
        )

        user = get_optional_user(credentials, db_session)

        assert user is None

    def test_get_optional_user_with_nonexistent_user(self, db_session: Session):
        """Test getting optional user when user doesn't exist."""
        nonexistent_id = uuid4()
        token = create_access_token(
            data={"sub": str(nonexistent_id), "email": "nonexistent@example.com"}
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        user = get_optional_user(credentials, db_session)

        assert user is None
