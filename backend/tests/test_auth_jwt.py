"""Tests for authentication JWT utilities."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from app.auth.jwt import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    get_user_id_from_token,
    validate_password_strength,
    verify_password,
)


class TestPasswordHashing:
    """Test password hashing functionality."""

    def test_get_password_hash_generates_hash(self):
        """Test that password hashing generates a valid hash."""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert hashed is not None
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password

    def test_verify_password_with_correct_password(self):
        """Test verifying password with correct password."""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_with_incorrect_password(self):
        """Test verifying password with incorrect password."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_with_different_hash(self):
        """Test verifying against a completely different hash."""
        password = "testpassword123"
        different_hash = get_password_hash("differentpassword")

        assert verify_password(password, different_hash) is False


class TestAccessToken:
    """Test JWT access token functionality."""

    def test_create_access_token(self):
        """Test creating an access token."""
        data = {"sub": str(uuid4()), "email": "test@example.com"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_custom_expiry(self):
        """Test creating token with custom expiration."""
        data = {"sub": str(uuid4())}
        expires = timedelta(minutes=30)
        token = create_access_token(data, expires_delta=expires)

        assert token is not None

        # Decode and verify expiration
        decoded = decode_access_token(token)
        assert decoded is not None
        assert "exp" in decoded

    def test_decode_access_token(self):
        """Test decoding a valid access token."""
        original_data = {"sub": str(uuid4()), "email": "test@example.com", "role": "user"}
        token = create_access_token(original_data)

        decoded = decode_access_token(token)

        assert decoded is not None
        assert decoded["sub"] == original_data["sub"]
        assert decoded["email"] == original_data["email"]
        assert decoded["role"] == original_data["role"]
        assert "exp" in decoded

    def test_decode_invalid_token(self):
        """Test decoding an invalid token."""
        invalid_token = "invalid.token.here"

        decoded = decode_access_token(invalid_token)

        assert decoded is None

    def test_decode_malformed_token(self):
        """Test decoding a malformed token."""
        malformed_token = "not.a.valid.jwt"

        decoded = decode_access_token(malformed_token)

        assert decoded is None


class TestGetUserIdFromToken:
    """Test extracting user ID from token."""

    def test_get_user_id_from_valid_token(self):
        """Test extracting user ID from a valid token."""
        user_id = uuid4()
        data = {"sub": str(user_id)}
        token = create_access_token(data)

        extracted_id = get_user_id_from_token(token)

        assert extracted_id is not None
        assert isinstance(extracted_id, UUID)
        assert extracted_id == user_id

    def test_get_user_id_from_token_without_sub(self):
        """Test extracting user ID from token without sub claim."""
        data = {"email": "test@example.com"}
        token = create_access_token(data)

        extracted_id = get_user_id_from_token(token)

        assert extracted_id is None

    def test_get_user_id_from_invalid_token(self):
        """Test extracting user ID from invalid token."""
        extracted_id = get_user_id_from_token("invalid.token")

        assert extracted_id is None

    def test_get_user_id_from_token_with_invalid_uuid(self):
        """Test extracting user ID when sub is not a valid UUID."""
        data = {"sub": "not-a-valid-uuid"}
        token = create_access_token(data)

        extracted_id = get_user_id_from_token(token)

        assert extracted_id is None


class TestValidatePasswordStrength:
    """Test password strength validation."""

    def test_valid_strong_password(self):
        """Test validation with a strong password."""
        password = "StrongPass1!"
        is_valid, error = validate_password_strength(password)

        assert is_valid is True
        assert error == ""

    def test_password_too_short(self):
        """Test validation with password that's too short."""
        password = "Short1!"
        is_valid, error = validate_password_strength(password)

        assert is_valid is False
        assert "8 characters" in error

    def test_password_no_uppercase(self):
        """Test validation with password missing uppercase."""
        password = "lowercase1!"
        is_valid, error = validate_password_strength(password)

        assert is_valid is False
        assert "uppercase" in error

    def test_password_no_lowercase(self):
        """Test validation with password missing lowercase."""
        password = "UPPERCASE1!"
        is_valid, error = validate_password_strength(password)

        assert is_valid is False
        assert "lowercase" in error

    def test_password_no_number(self):
        """Test validation with password missing number."""
        password = "NoNumberPass!"
        is_valid, error = validate_password_strength(password)

        assert is_valid is False
        assert "number" in error

    def test_password_no_special_char(self):
        """Test validation with password missing special character."""
        password = "NoSpecialChar1"
        is_valid, error = validate_password_strength(password)

        assert is_valid is False
        assert "special character" in error

    def test_password_with_sql_injection_attempt(self):
        """Test validation with SQL injection attempt."""
        password = "Password1!'; DROP TABLE users; --"
        is_valid, error = validate_password_strength(password)

        assert is_valid is False
        assert "invalid characters" in error

    def test_password_exactly_8_chars(self):
        """Test validation with password exactly 8 characters."""
        password = "Pass1!ab"  # 8 characters
        is_valid, error = validate_password_strength(password)

        assert is_valid is True
        assert error == ""

    @pytest.mark.parametrize(
        "password,expected_valid",
        [
            ("Test123!", True),
            ("HelloWorld1@", True),
            ("MyP@ssw0rd", True),
            ("weak", False),
            ("12345678", False),
            ("password", False),
            ("PASSWORD", False),
            ("Pass word1!", True),  # Space is a valid special char
        ],
    )
    def test_various_passwords(self, password, expected_valid):
        """Test various password combinations."""
        is_valid, _ = validate_password_strength(password)
        assert is_valid == expected_valid
