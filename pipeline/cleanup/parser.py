"""Location parsing logic for cleanup module."""

from __future__ import annotations

import re

from pipeline.location.cache import ParsedLocation, get_location_cache
from pipeline.location.simple_parser import normalize_location

PLAIN_REMOTE_PATTERNS = [
    r"^remote$",
    r"^work from home$",
    r"^wfh$",
    r"^distributed$",
    r"^virtual$",
    r"^telecommute$",
    r"^anywhere$",
]


def _is_plain_remote(location: str) -> bool:
    loc_lower = location.lower().strip()
    for pattern in PLAIN_REMOTE_PATTERNS:
        if re.match(pattern, loc_lower, re.IGNORECASE):
            return True
    return False


def _normalize_for_comparison(value: str | None) -> str:
    if not value:
        return ""
    normalized = re.sub(r"[^\w\s]", "", value.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _contains_normalized(haystack: str, needle: str) -> bool:
    haystack_norm = _normalize_for_comparison(haystack)
    needle_norm = _normalize_for_comparison(needle)
    return needle_norm in haystack_norm


def _is_metadata_consistent(
    location_str: str, parsed_from_location: dict, metadata_result: dict
) -> bool:
    if _is_plain_remote(location_str) and metadata_result.get("country"):
        return False

    location_city = parsed_from_location.get("city")
    metadata_city = metadata_result.get("city")

    if location_city and metadata_city:
        if not _contains_normalized(location_str, metadata_city):
            return False

    location_country = parsed_from_location.get("country")
    metadata_country = metadata_result.get("country")

    if location_country and metadata_country:
        if not _contains_normalized(location_str, metadata_country):
            country_variations = {
                "united states": ["us", "usa", "united states of america", "america"],
                "united kingdom": ["uk", "britain", "great britain", "england"],
                "canada": ["ca"],
            }
            loc_country_norm = _normalize_for_comparison(location_country)
            meta_country_norm = _normalize_for_comparison(metadata_country)

            found_match = False
            for country, variations in country_variations.items():
                if loc_country_norm == country or loc_country_norm in variations:
                    if meta_country_norm == country or meta_country_norm in variations:
                        found_match = True
                        break

            if not found_match and loc_country_norm != meta_country_norm:
                return False

    return True


async def _parse_location_only(location: str) -> dict:
    cache = await get_location_cache()

    cached = await cache.get(location)
    if cached:
        return {
            "city": cached.city,
            "state": cached.state,
            "country": cached.country,
        }

    result = normalize_location(location)
    parsed = {
        "city": result.get("city"),
        "state": result.get("state"),
        "country": result.get("country"),
    }

    await cache.set(
        location,
        ParsedLocation(
            city=parsed["city"],
            state=parsed["state"],
            country=parsed["country"],
            is_remote=result.get("is_remote", False),
        ),
    )

    return parsed
