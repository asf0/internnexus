"""Centralized error handling for the API."""

from __future__ import annotations

from typing import Any


class APIError(Exception):
    """Base API error with structured response."""

    def __init__(
        self,
        error: str,
        message: str,
        status_code: int = 400,
        action: str | None = None,
        **extra: Any,
    ):
        self.error = error
        self.message = message
        self.status_code = status_code
        self.action = action
        self.extra = extra
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response."""
        result: dict[str, Any] = {
            "error": self.error,
            "message": self.message,
        }
        if self.action:
            result["action"] = self.action
        result.update(self.extra)
        return result


class AuthenticationError(APIError):
    """Authentication related errors."""

    def __init__(self, message: str, action: str | None = None, **extra: Any):
        super().__init__(
            error="AUTHENTICATION_ERROR",
            message=message,
            status_code=401,
            action=action,
            **extra,
        )


class AuthorizationError(APIError):
    """Authorization related errors."""

    def __init__(self, message: str = "Not authorized", action: str | None = None, **extra: Any):
        super().__init__(
            error="AUTHORIZATION_ERROR",
            message=message,
            status_code=403,
            action=action,
            **extra,
        )


class NotFoundError(APIError):
    """Resource not found errors."""

    def __init__(self, message: str = "Resource not found", **extra: Any):
        super().__init__(
            error="NOT_FOUND",
            message=message,
            status_code=404,
            **extra,
        )


class ConflictError(APIError):
    """Conflict errors (e.g., duplicate resource)."""

    def __init__(self, message: str, action: str | None = None, **extra: Any):
        super().__init__(
            error="CONFLICT",
            message=message,
            status_code=409,
            action=action,
            **extra,
        )


class ValidationError(APIError):
    """Validation errors."""

    def __init__(self, message: str, **extra: Any):
        super().__init__(
            error="VALIDATION_ERROR",
            message=message,
            status_code=422,
            **extra,
        )


class AuthErrorMessages:
    """Standard auth error messages."""

    INVALID_CREDENTIALS = "Invalid email or password."
    EMAIL_ALREADY_REGISTERED = "An account with this email already exists. Please sign in instead."
    EMAIL_REGISTERED_WITH_OAUTH = (
        "This email is already registered with {providers}. "
        "Please sign in with that provider or set a password for your account."
    )
    OAUTH_ACCOUNT_NO_PASSWORD = (
        "This account uses {providers} authentication. "
        "Please sign in with that provider or set a password first."
    )
    OAUTH_VERIFICATION_FAILED = "Failed to verify {provider} token: {message}"
    TOKEN_INVALID = "Invalid or expired token."
    TOKEN_EXPIRED = "Token has expired. Please log in again."
    TOKEN_INVALIDATED = "Token invalidated by password change. Please log in again."


def create_auth_error(
    error: str,
    message: str,
    action: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Create a standardized auth error response."""
    detail: dict[str, Any] = {"error": error, "message": message}
    if action:
        detail["action"] = action
    detail.update(extra)
    return detail
