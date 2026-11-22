"""City recognition, validation, and country inference from city names."""

from __future__ import annotations

import re

from pipeline.stages.cleanup.location._patterns import (
    _CITY_SUFFIX_PATTERN,
    _FAKE_CITY_PATTERNS,
    _FAKE_CITY_PREFIX_PATTERN,
    _STREET_NUMBER_PATTERN,
    _STREET_TYPE_PATTERN,
    _SUITE_PATTERN,
    _TRAILING_STATE_PATTERN,
    _WHITESPACE_PATTERN,
    _ZIP_PATTERN,
)
from pipeline.stages.cleanup.location.constants import (
    COUNTRY_UNITED_STATES,
    COUNTRIES_AS_CITIES,
    INVALID_CITY_PATTERNS,
    INTERNATIONAL_CITIES,
    MAJOR_CITY_STATE_NAMES,
    STATES_AS_CITIES,
    US_CITIES,
)


def is_street_address(text: str) -> bool:
    """Check if text looks like a street address using pre-compiled pattern."""
    return bool(_STREET_NUMBER_PATTERN.match(text.strip()))


def is_fake_city(city: str) -> bool:
    """Check if city name is fake/artificial using pre-compiled patterns."""
    if not city:
        return True

    city_lower = city.lower().strip()

    # Check fake indicators using pre-compiled patterns
    for pattern in _FAKE_CITY_PATTERNS:
        if pattern.search(city_lower):
            return True

    # Check for patterns like "Suite 1", "Remote Us"
    if _FAKE_CITY_PREFIX_PATTERN.match(city_lower):
        return True

    return False


def extract_city_from_street_address(street_text: str) -> str | None:
    """Extract city name from street address text using pre-compiled patterns."""
    if not street_text:
        return None

    # Remove leading street number and type
    text = _STREET_TYPE_PATTERN.sub("", street_text)

    # Remove suite/apartment/unit info
    text = _SUITE_PATTERN.sub(" ", text)

    # Remove extra spaces
    text = _WHITESPACE_PATTERN.sub(" ", text).strip()

    city = text.strip()

    if is_fake_city(city):
        return None

    return city if city else None


def extract_city_before_state(text: str) -> str | None:
    """Extract city that appears before state abbreviation."""
    if not text:
        return None

    parts = text.split()

    if len(parts) >= 2:
        last_part = parts[-1]
        if re.match(r"^[A-Z]{2}$", last_part):
            city = " ".join(parts[:-1])
            return city if not is_fake_city(city) else None

    if re.match(r"^[A-Z]{2}(\s+\d{5})?$", text.strip()):
        return None

    if not is_fake_city(text):
        return text.strip()

    return None


def _strip_zip_code(text: str) -> str:
    """Remove trailing ZIP code from text."""
    return _ZIP_PATTERN.sub("", text).strip()


def clean_city_name(city: str | None) -> str | None:
    """Clean city name by removing common suffixes and validating against invalid values."""
    if not city:
        return None
    city = city.strip()
    if _is_invalid_city_name(city):
        return None
    city = _city_after_region_prefix(city)
    if _is_invalid_city_name(city):
        return None
    city = _ZIP_PATTERN.sub("", _CITY_SUFFIX_PATTERN.sub("", _TRAILING_STATE_PATTERN.sub("", city))).strip()
    return None if not city or _is_invalid_city_name(city) else city


def is_country_or_state_name(city: str) -> bool:
    """Whether a token is a country or a non-major-state masquerading as a city."""
    normalized = city.lower()
    if normalized in COUNTRIES_AS_CITIES:
        return True
    return normalized in STATES_AS_CITIES and normalized not in MAJOR_CITY_STATE_NAMES


def _is_invalid_city_name(city: str) -> bool:
    """Whether a candidate is a country, non-city state, or known invalid form."""
    if is_country_or_state_name(city):
        return True
    return any(pattern.search(city) for pattern in INVALID_CITY_PATTERNS)


def _city_after_region_prefix(city: str) -> str:
    """Strip a recognized ``Country - City`` prefix without touching other dashes."""
    if " - " not in city:
        return city
    prefix, candidate = city.split(" - ", 1)
    if prefix.strip().lower() in COUNTRIES_AS_CITIES or prefix.strip().lower() in STATES_AS_CITIES:
        return candidate.strip()
    return city


def infer_country_from_city(city: str | None) -> str | None:
    """Infer country from city name using lookup table."""
    if not city or is_fake_city(city):
        return None
    city_lower = city.lower()
    if city_lower in US_CITIES:
        return COUNTRY_UNITED_STATES
    return INTERNATIONAL_CITIES.get(city_lower)
