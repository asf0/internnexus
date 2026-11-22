from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
import jwt
from jwt.exceptions import InvalidTokenError

from app.infra.config import get_settings
import re

# Password hashing context using Argon2
ph = PasswordHasher()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except (VerificationError, InvalidHashError):
        return False


def get_password_hash(password: str) -> str:
    """Hash a plain password."""
    return ph.hash(password)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
    password_changed_at: datetime | None = None,
    *,
    jti: str | None = None,
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
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

    now = issued_at or datetime.now(timezone.utc)
    to_encode["jti"] = jti or str(uuid4())
    to_encode["iat"] = now

    if password_changed_at:
        to_encode["pw_changed"] = password_changed_at.timestamp()

    if expires_at is not None:
        expire = expires_at
    elif expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(hours=settings.jwt_expiration_hours)

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
        payload = jwt.decode(
            token,
            settings.auth_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "jti", "iat", "exp"]},
        )
        return payload
    except InvalidTokenError:
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
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"

    # Check for special character
    special_chars = r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]"
    if not re.search(special_chars, password):
        return (
            False,
            "Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)",
        )

    return True, ""


def ensure_password_strength(password: str) -> str:
    """Return *password* if strong enough, else raise ``ValueError``.

    Pydantic field validators translate the ``ValueError`` into a 422; this
    keeps the strength policy and messages defined in exactly one place.
    """
    is_valid, error_message = validate_password_strength(password)
    if not is_valid:
        raise ValueError(error_message)
    return password
