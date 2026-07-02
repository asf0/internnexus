"""Top-level location normalization orchestration.

``normalize_location`` splits input into city, state, country, and remote
metadata while delegating focused parsing to the country, state, and city
modules.
"""

from __future__ import annotations

from typing import Any

from pipeline.location._patterns import (
    _CITY_STATE_PATTERN,
    _MULTI_LOC_DELIMITERS,
    _REMOTE_PATTERNS,
)
from pipeline.location.city_parser import (
    clean_city_name,
    extract_city_before_state,
    extract_city_from_street_address,
    infer_country_from_city,
    is_fake_city,
    is_street_address,
)
from pipeline.location.constants import (
    COUNTRY_UNITED_STATES,
    COUNTRIES_AS_CITIES,
    MAJOR_CITY_STATE_NAMES,
    SINGLE_PART_COUNTRY_NAMES,
    STATES_AS_CITIES,
)
from pipeline.location.country_parser import extract_country_from_text
from pipeline.location.state_parser import (
    expand_state_abbreviation,
    extract_state,
    infer_country_from_state,
    normalize_state_name,
)


def is_remote_pattern(location: str) -> bool:
    """Check if location is a remote pattern using pre-compiled patterns."""
    location_lower = location.lower().strip()

    for pattern in _REMOTE_PATTERNS:
        if pattern.search(location_lower):
            return True
    return False


def has_multiple_remote_locations(location: str) -> bool:
    """Check if location has multiple remote locations using pre-compiled patterns."""
    if ";" not in location and "|" not in location:
        return False

    parts = _MULTI_LOC_DELIMITERS.split(location)
    remote_count = sum(1 for part in parts if is_remote_pattern(part.strip()))

    return remote_count > 1 or (len(parts) > 1 and is_remote_pattern(location))


def _build_empty_result(location: str | None) -> dict[str, Any]:
    """Return the default result dict for normalize_location."""
    return {
        "full": location,
        "city": None,
        "state": None,
        "country": None,
        "all_cities": None,
        "is_remote": False,
        "is_multi_location": False,
    }


def _detect_remote(location_clean: str, location_lower: str) -> dict[str, Any] | None:
    """Detect remote-only and remote-with-country location forms."""
    if has_multiple_remote_locations(location_clean):
        return {"is_remote": True, "is_multi_location": True}
    if location_lower == "remote":
        return {"is_remote": True}
    if location_lower.startswith("remote") and is_remote_pattern(location_clean):
        return {"country": extract_country_from_text(location_clean), "is_remote": True}
    return None


def _split_and_clean_parts(location_clean: str) -> tuple[list[str], bool]:
    """Split by comma, strip trailing remote/hybrid indicator, and collapse multi-location."""
    parts = [p.strip() for p in location_clean.split(",")]
    parts = [p for p in parts if p]

    is_remote_job = False
    if parts and parts[-1].lower() in {"remote", "hybrid", "virtual", "work from home", "wfh"}:
        parts = parts[:-1]
        is_remote_job = True

    if len(parts) == 1 and (";" in parts[0] or "|" in parts[0]):
        first_loc = parts[0].split(";")[0].split("|")[0].strip()
        parts = [first_loc]

    return parts, is_remote_job


def _parse_one_part(first_part: str, country: str | None) -> tuple[str | None, str | None, str | None]:
    """Parse a single-part location into city/state/country."""
    city: str | None = None
    state: str | None = None

    if is_street_address(first_part):
        city = extract_city_from_street_address(first_part)
        if not city:
            city = extract_city_before_state(first_part)
        state = extract_state(first_part)
        return city, state, country

    if is_fake_city(first_part):
        return None, None, country

    potential_country = extract_country_from_text(first_part)
    if potential_country and first_part.lower() in SINGLE_PART_COUNTRY_NAMES:
        return None, None, potential_country

    city_state_match = _CITY_STATE_PATTERN.match(first_part.strip())
    if city_state_match:
        potential_city = city_state_match.group(1).strip()
        state_abbr = city_state_match.group(2)
        if not is_fake_city(potential_city):
            city = potential_city
            inferred_country = infer_country_from_city(potential_city)
            state = expand_state_abbreviation(state_abbr, inferred_country)
        return city, state, country

    inferred_country = infer_country_from_city(first_part)
    if inferred_country:
        return first_part, None, inferred_country

    if extract_state(first_part):
        return None, extract_state(first_part), country

    return first_part, None, country


def _parse_two_parts(first: str, second: str, country: str | None) -> tuple[str | None, str | None, str | None]:
    """Parse a two-part location into city/state/country."""
    city: str | None = None
    state: str | None = None

    second_country = extract_country_from_text(second)
    first_state = extract_state(first, second_country)
    second_state = extract_state(second, second_country)
    if first_state and second_state and first_state != second_state:
        return None, None, COUNTRY_UNITED_STATES

    if is_street_address(first):
        city = extract_city_from_street_address(first)
        state = extract_state(second, second_country)
        if not city:
            city = extract_city_before_state(second)
        return city, state, country

    state = extract_state(second, second_country)
    if state:
        return first if not is_fake_city(first) else None, state, country

    if second_country and len(second.strip()) <= 20:
        first_state = extract_state(first, second_country)
        if first_state and infer_country_from_state(first_state) == second_country:
            return None, first_state, second_country
        return first if not is_fake_city(first) else None, None, second_country

    return first if not is_fake_city(first) else None, None, country


def _parse_three_or_more(parts: list[str], country: str | None) -> tuple[str | None, str | None, str | None]:
    """Parse a three-or-more-part location into city/state/country."""
    detected_country = extract_country_from_text(parts[-1])

    if is_street_address(parts[0]):
        city = parts[1] if not is_fake_city(parts[1]) else None
        state = extract_state(parts[2], detected_country) if len(parts) > 2 else None
        return city, state, detected_country or country

    city = parts[0] if not is_fake_city(parts[0]) else None
    potential_state = extract_state(parts[1], detected_country)
    if potential_state and city and potential_state.lower() == city.lower():
        state = None
    else:
        state = potential_state

    if not state and len(parts) > 2:
        potential_country = extract_country_from_text(parts[2])
        if potential_country:
            country = potential_country

    return city, state, detected_country or country


def _infer_and_validate_country(
    city: str | None,
    state: str | None,
    country: str | None,
) -> tuple[str | None, str | None]:
    """Infer country from state/city and clear city when it is actually a country/state."""
    if not country:
        country = infer_country_from_state(state)

    inferred_from_city = None
    if not country and city:
        inferred_from_city = infer_country_from_city(city)

    if city:
        city_lower = city.lower()
        if city_lower in COUNTRIES_AS_CITIES:
            if inferred_from_city:
                country = inferred_from_city
            city = None
        elif city_lower in STATES_AS_CITIES and city_lower not in MAJOR_CITY_STATE_NAMES:
            if inferred_from_city:
                country = inferred_from_city
            city = None

    if not country and city:
        country = infer_country_from_city(city)

    return country, city


def normalize_location(location: str | None) -> dict[str, Any]:
    """
    Normalize location string into city, state, country.

    This is the main entry point - replaces the old geostring-based parser.
    """
    empty_result = _build_empty_result(location)

    if not location or not location.strip():
        return empty_result

    location_clean = location.strip()
    location_lower = location_clean.lower()

    remote_flags = _detect_remote(location_clean, location_lower)
    if remote_flags is not None:
        return {**empty_result, **remote_flags}

    country = extract_country_from_text(location_clean)
    parts, is_remote_job = _split_and_clean_parts(location_clean)

    if not parts:
        if is_remote_job:
            return {**empty_result, "country": country, "is_remote": True}
        return empty_result

    city: str | None = None
    state: str | None = None

    if len(parts) == 1:
        city, state, country = _parse_one_part(parts[0], country)
    elif len(parts) == 2:
        city, state, country = _parse_two_parts(parts[0], parts[1], country)
    else:
        city, state, country = _parse_three_or_more(parts, country)

    if state:
        state = normalize_state_name(state)

    if city:
        city = clean_city_name(city)
        if city and city.lower() not in location_lower:
            city = None

    country, city = _infer_and_validate_country(city, state, country)

    full_parts = [p for p in [city, state, country] if p]
    full_location = ", ".join(full_parts) if full_parts else location_clean

    return {
        "full": full_location,
        "city": city,
        "state": state,
        "country": country,
        "all_cities": city,
        "is_remote": is_remote_job,
        "is_multi_location": False,
    }
