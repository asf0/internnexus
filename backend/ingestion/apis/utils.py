"""Shared utilities for ATS API clients."""

from __future__ import annotations

from datetime import datetime


def parse_iso_datetime(value: str | None) -> datetime | None:
    """Parse ISO 8601 datetime string to datetime object.

    Handles both 'Z' suffix and explicit timezone offsets.

    Args:
        value: ISO 8601 datetime string (e.g., "2024-01-15T10:30:00Z")

    Returns:
        datetime object or None if parsing fails
    """
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_unix_timestamp(value: int | None) -> datetime | None:
    """Parse Unix timestamp (milliseconds) to datetime object.

    Used by Lever API which returns timestamps in milliseconds.

    Args:
        value: Unix timestamp in milliseconds

    Returns:
        datetime object or None if parsing fails
    """
    if not value:
        return None
    try:
        return datetime.utcfromtimestamp(value / 1000)
    except (TypeError, ValueError, OSError):
        return None
