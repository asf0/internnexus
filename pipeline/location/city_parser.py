"""City recognition, validation, and country inference from city names."""

from __future__ import annotations

import re

from pipeline.location._patterns import (
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
from pipeline.location.constants import (
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

    # Check if city is actually a country
    if city.lower() in COUNTRIES_AS_CITIES:
        return None

    if city.lower() in STATES_AS_CITIES and city.lower() not in MAJOR_CITY_STATE_NAMES:
        return None

    # Check against invalid city patterns (multi-location, addresses, etc.)
    for pattern in INVALID_CITY_PATTERNS:
        if pattern.search(city):
            return None

    # Handle "Country - City" or "Region - City" patterns
    # e.g., "Australia - Sydney" -> "Sydney", "India - Pune" -> "Pune"
    if " - " in city:
        parts = city.split(" - ", 1)
        if len(parts) == 2:
            potential_city = parts[1].strip()
            # Verify the first part is a country/region and second is a valid city
            first_part = parts[0].strip().lower()
            if first_part in COUNTRIES_AS_CITIES or first_part in STATES_AS_CITIES:
                # Extract just the city part
                city = potential_city
                # Re-validate the extracted city
                if city.lower() in COUNTRIES_AS_CITIES:
                    return None
                if city.lower() in STATES_AS_CITIES and city.lower() not in MAJOR_CITY_STATE_NAMES:
                    return None

    # Remove state abbreviation if present
    city = _TRAILING_STATE_PATTERN.sub("", city)

    # Remove common suffixes
    city = _CITY_SUFFIX_PATTERN.sub("", city)

    # Remove zip codes
    city = _ZIP_PATTERN.sub("", city)

    city = city.strip()

    # After cleaning, check again if it's a country/state
    if city.lower() in COUNTRIES_AS_CITIES:
        return None
    if city.lower() in STATES_AS_CITIES and city.lower() not in MAJOR_CITY_STATE_NAMES:
        return None

    return city if city else None


def infer_country_from_city(city: str | None) -> str | None:
    """Infer country from city name using lookup table."""
    if not city or is_fake_city(city):
        return None
    city_lower = city.lower()
    if city_lower in US_CITIES:
        return COUNTRY_UNITED_STATES
    return INTERNATIONAL_CITIES.get(city_lower)
