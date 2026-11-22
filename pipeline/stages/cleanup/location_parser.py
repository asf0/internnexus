"""Location parsing logic for cleanup module."""

from __future__ import annotations

import re

from pipeline.stages.cleanup.data.loader import _OVERRIDES as LOCATION_OVERRIDES
from pipeline.stages.cleanup.data.loader import _PATTERNS as PLAIN_REMOTE_PATTERNS
from pipeline.stages.cleanup.location.cache import ParsedLocation, get_location_cache
from pipeline.stages.cleanup.location.normalize import normalize_location


def _is_plain_remote(location: str) -> bool:
    loc_lower = location.lower().strip()
    for pattern in PLAIN_REMOTE_PATTERNS:
        if re.match(pattern, loc_lower, re.IGNORECASE):
            return True
    return False


def _parse_location_only(location: str) -> dict:
    cache = get_location_cache()

    cached = cache.get(location)
    if cached:
        return {
            "city": cached.city,
            "state": cached.state,
            "country": cached.country,
        }

    location_key = location.strip().lower()
    override = LOCATION_OVERRIDES.get(location_key)
    if override is not None:
        cache.set(
            location,
            ParsedLocation(
                city=override["city"],
                state=override["state"],
                country=override["country"],
                is_remote=False,
            ),
        )
        return override

    result = normalize_location(location)
    parsed = {
        "city": result.get("city"),
        "state": result.get("state"),
        "country": result.get("country"),
    }

    cache.set(
        location,
        ParsedLocation(
            city=parsed["city"],
            state=parsed["state"],
            country=parsed["country"],
            is_remote=result.get("is_remote", False),
        ),
    )

    return parsed
