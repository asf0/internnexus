from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from app.config import get_settings
import re

# Password hashing context using Argon2
ph = PasswordHasher()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except VerifyMismatchError:
        return False


def get_password_hash(password: str) -> str:
    """Hash a plain password."""
    return ph.hash(password)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
    password_changed_at: datetime | None = None,
) -> str:
    """Create a JWT access token.

    Args:
        data: The data to encode in the token (typically contains user_id, email)
        expires_delta: Optional custom expiration time, defaults to 24 hours
        password_changed_at: Optional timestamp of last password change for invalidation

    Returns:
        The encoded JWT token string
    """
    to_encode = data.copy()
    settings = get_settings()

    # Add unique JWT ID (jti) claim to ensure token uniqueness (RFC 7519)
    to_encode["jti"] = str(uuid4())

    if password_changed_at:
        to_encode["pw_changed"] = password_changed_at.timestamp()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=24)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, settings.auth_secret, algorithm=settings.jwt_algorithm)

    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT access token.

    Args:
        token: The JWT token string to decode

    Returns:
        The decoded token payload if valid, None otherwise
    """
    try:
        settings = get_settings()
        payload = jwt.decode(token, settings.auth_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength.

    Args:
        password: The plain password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """

    # Check minimum length
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    # Check for uppercase letter
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"

    # Check for lowercase letter
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"

    # Check for number
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number"

    # Check for special character
    special_chars = r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]"
    if not re.search(special_chars, password):
        return (
            False,
            "Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)",
        )

    return True, ""
