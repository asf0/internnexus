"""Unit tests for JWT module - password hashing and token management."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from jose import jwt as jose_jwt

from app.auth.jwt import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    validate_password_strength,
)


class TestPasswordHashing:
    """Test suite for password hashing functions."""

    def test_get_password_hash(self):
        """Test that password hashing produces a valid hash."""
        # Arrange
        password = "SecurePass123!"

        # Act
        hashed = get_password_hash(password)

        # Assert
        assert hashed != password
        assert len(hashed) > 0
        assert "$argon2id" in hashed

    def test_verify_password_correct(self):
        """Test verifying correct password."""
        # Arrange
        password = "SecurePass123!"
        hashed = get_password_hash(password)

        # Act
        result = verify_password(password, hashed)

        # Assert
        assert result is True

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        # Arrange
        password = "SecurePass123!"
        wrong_password = "WrongPass123!"
        hashed = get_password_hash(password)

        # Act
        result = verify_password(wrong_password, hashed)

        # Assert
        assert result is False

    def test_verify_password_different_hash(self):
        """Test that same password produces different hashes."""
        # Arrange
        password = "SecurePass123!"

        # Act
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Assert
        assert hash1 != hash2
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestAccessToken:
    """Test suite for JWT access token functions."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for JWT."""
        with patch("app.auth.jwt.get_settings") as mock:
            mock_settings = Mock()
            mock_settings.auth_secret = "test-secret-key-32-characters-long"
            mock_settings.jwt_algorithm = "HS256"
            mock.return_value = mock_settings
            yield mock

    def test_create_access_token(self, mock_settings):
        """Test creating a basic access token."""
        # Arrange
        data = {"sub": "user-123", "email": "test@example.com"}

        # Act
        token = create_access_token(data)

        # Assert
        assert token is not None
        assert isinstance(token, str)
        # Should be 3 parts separated by dots
        assert len(token.split(".")) == 3

    def test_create_access_token_with_expiration(self, mock_settings):
        """Test creating token with custom expiration."""
        # Arrange
        data = {"sub": "user-123"}
        expires_delta = timedelta(hours=2)

        # Act
        token = create_access_token(data, expires_delta=expires_delta)
        decoded = decode_access_token(token)

        # Assert
        assert decoded is not None
        assert decoded["sub"] == "user-123"
        assert "exp" in decoded

    def test_create_access_token_with_password_changed(self, mock_settings):
        """Test creating token with password change timestamp."""
        # Arrange
        data = {"sub": "user-123"}
        password_changed_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        # Act
        token = create_access_token(data, password_changed_at=password_changed_at)
        decoded = decode_access_token(token)

        # Assert
        assert decoded is not None
        assert "pw_changed" in decoded
        assert decoded["pw_changed"] == password_changed_at.timestamp()

    def test_create_access_token_includes_jti(self, mock_settings):
        """Test that token includes unique JWT ID."""
        # Arrange
        data = {"sub": "user-123"}

        # Act
        token1 = create_access_token(data)
        token2 = create_access_token(data)
        decoded1 = decode_access_token(token1)
        decoded2 = decode_access_token(token2)

        # Assert
        assert decoded1["jti"] != decoded2["jti"]

    def test_decode_access_token_valid(self, mock_settings):
        """Test decoding a valid token."""
        # Arrange
        data = {"sub": "user-123", "email": "test@example.com"}
        token = create_access_token(data)

        # Act
        decoded = decode_access_token(token)

        # Assert
        assert decoded is not None
        assert decoded["sub"] == "user-123"
        assert decoded["email"] == "test@example.com"

    def test_decode_access_token_invalid(self, mock_settings):
        """Test decoding an invalid token."""
        # Arrange
        invalid_token = "invalid.token.here"

        # Act
        decoded = decode_access_token(invalid_token)

        # Assert
        assert decoded is None

    def test_decode_access_token_expired(self, mock_settings):
        """Test decoding an expired token."""
        # Arrange
        data = {"sub": "user-123"}
        expired_delta = timedelta(seconds=-1)
        token = create_access_token(data, expires_delta=expired_delta)

        # Act
        decoded = decode_access_token(token)

        # Assert
        assert decoded is None

    def test_decode_access_token_wrong_secret(self, mock_settings):
        """Test decoding with wrong secret."""
        # Arrange
        data = {"sub": "user-123"}
        token = create_access_token(data)

        # Change settings to different secret
        mock_settings.return_value.auth_secret = "different-secret"

        # Act
        decoded = decode_access_token(token)

        # Assert
        assert decoded is None


class TestValidatePasswordStrength:
    """Test suite for password strength validation."""

    def test_valid_strong_password(self):
        """Test validation of strong password."""
        # Arrange
        password = "SecurePass123!"

        # Act
        is_valid, error = validate_password_strength(password)

        # Assert
        assert is_valid is True
        assert error == ""

    def test_password_too_short(self):
        """Test validation fails for short password."""
        # Arrange
        password = "Short1!"

        # Act
        is_valid, error = validate_password_strength(password)

        # Assert
        assert is_valid is False
        assert "8 characters" in error

    def test_password_no_uppercase(self):
        """Test validation fails for password without uppercase."""
        # Arrange
        password = "securepass123!"

        # Act
        is_valid, error = validate_password_strength(password)

        # Assert
        assert is_valid is False
        assert "uppercase" in error.lower()

    def test_password_no_lowercase(self):
        """Test validation fails for password without lowercase."""
        # Arrange
        password = "SECUREPASS123!"

        # Act
        is_valid, error = validate_password_strength(password)

        # Assert
        assert is_valid is False
        assert "lowercase" in error.lower()

    def test_password_no_number(self):
        """Test validation fails for password without number."""
        # Arrange
        password = "SecurePass!!!"

        # Act
        is_valid, error = validate_password_strength(password)

        # Assert
        assert is_valid is False
        assert "number" in error.lower()

    def test_password_no_special_char(self):
        """Test validation fails for password without special character."""
        # Arrange
        password = "SecurePass123"

        # Act
        is_valid, error = validate_password_strength(password)

        # Assert
        assert is_valid is False
        assert "special character" in error.lower()

    def test_password_multiple_requirements_missing(self):
        """Test that only first missing requirement is reported."""
        # Arrange
        password = "short"  # Missing: length, uppercase, number, special

        # Act
        is_valid, error = validate_password_strength(password)

        # Assert
        assert is_valid is False
        # Should report first issue (length)
        assert "8 characters" in error

    @pytest.mark.parametrize(
        "password,expected_valid",
        [
            ("A1!aaaaa", True),  # Minimum length with all requirements
            ("Test123!@#", True),  # Good password
            ("MyP@ssw0rd", True),  # Good password
            ("C0mpl3x!Pass", True),  # Complex password
            ("a", False),  # Way too short
            ("password", False),  # No uppercase, no number, no special
            ("PASSWORD", False),  # No lowercase, no number, no special
            ("12345678", False),  # Only numbers
            ("!!!!!!!!", False),  # Only special chars
        ],
    )
    def test_various_passwords(self, password, expected_valid):
        """Test various password combinations."""
        is_valid, _ = validate_password_strength(password)
        assert is_valid == expected_valid
