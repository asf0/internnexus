"""Shared utilities for ATS API clients."""

from __future__ import annotations

from datetime import datetime
import re
from typing import Literal


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_unix_timestamp(value: int | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.utcfromtimestamp(value / 1000)
    except (TypeError, ValueError, OSError):
        return None


def parse_job_type(value: str | None) -> Literal["internship", "full_time", "part_time"] | None:
    if not value:
        return None
    value_lower = value.lower().strip()
    if "intern" in value_lower:
        return "internship"
    if "part" in value_lower and "time" in value_lower:
        return "part_time"
    if "full" in value_lower and "time" in value_lower:
        return "full_time"
    if value_lower in ("full-time", "fulltime", "permanent"):
        return "full_time"
    if value_lower in ("part-time", "parttime"):
        return "part_time"
    return None


def parse_work_mode(value: str | None) -> Literal["remote", "hybrid", "on_site"] | None:
    if not value:
        return None
    value_lower = value.lower().strip()
    if "remote" in value_lower:
        return "remote"
    if "hybrid" in value_lower:
        return "hybrid"
    if any(p in value_lower for p in ["on-site", "onsite", "in-office", "inoffice"]):
        return "on_site"
    return None


def detect_job_type_from_title(
    title: str,
) -> Literal["internship", "full_time", "part_time"] | None:
    if not title:
        return None
    title_lower = title.lower()
    if "intern" in title_lower:
        return "internship"
    if re.search(r"part[\s-]?time", title_lower):
        return "part_time"
    return None


def detect_work_mode_from_text(
    title: str, location: str
) -> Literal["remote", "hybrid", "on_site"] | None:
    combined = f"{title} {location}".lower()
    if "remote" in combined:
        return "remote"
    if "hybrid" in combined:
        return "hybrid"
    if any(p in combined for p in ["on-site", "onsite", "in-office"]):
        return "on_site"
    return None
