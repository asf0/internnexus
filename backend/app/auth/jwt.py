from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a plain password."""
    return pwd_context.hash(password)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token.

    Args:
        data: The data to encode in the token (typically contains user_id, email)
        expires_delta: Optional custom expiration time, defaults to 24 hours

    Returns:
        The encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=24)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT access token.

    Args:
        token: The JWT token string to decode

    Returns:
        The decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None


def get_user_id_from_token(token: str) -> UUID | None:
    """Extract user_id from a JWT token.

    Args:
        token: The JWT token string

    Returns:
        The user UUID if valid, None otherwise
    """
    payload = decode_access_token(token)
    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    try:
        return UUID(user_id)
    except ValueError:
        return None


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength.

    Args:
        password: The plain password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    import re

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

    # Check for SQL injection attempts
    if re.search(r"['\";--]", password):
        return False, "Password contains invalid characters"

    return True, ""
