"""State / province extraction and normalization."""

from __future__ import annotations

from pipeline.location._patterns import _STATE_ABBR_PATTERN
from pipeline.location.city_parser import _strip_zip_code
from pipeline.location.constants import (
    ABBR_TO_STATE,
    AUSTRALIAN_STATES,
    BRAZILIAN_STATES,
    CANADIAN_PROVINCES,
    COUNTRY_AUSTRALIA,
    COUNTRY_CANADA,
    COUNTRY_GERMANY,
    COUNTRY_INDIA,
    COUNTRY_NAMES_AS_STATES,
    COUNTRY_UNITED_STATES,
    FRENCH_REGIONS,
    GERMAN_STATES,
    INDIAN_STATE_ABBR,
    INDIAN_STATES,
    ITALIAN_REGIONS,
    MEXICAN_STATES,
    SPANISH_REGIONS,
    STATE_MAPPINGS,
    UK_REGIONS,
    US_STATES_FULL,
)


def expand_state_abbreviation(state_abbr: str, country_hint: str | None = None) -> str | None:
    """Expand state abbreviation based on country context.

    Args:
        state_abbr: Two-letter state abbreviation (e.g., "TN", "KA")
        country_hint: Optional country name to resolve ambiguous abbreviations.
                     If India, uses Indian state abbreviations.
                     If None or other countries, uses US/Canadian abbreviations.

    Returns:
        Full state name or None if not found.
    """
    abbr_upper = state_abbr.upper()

    if country_hint == COUNTRY_INDIA:
        return INDIAN_STATE_ABBR.get(abbr_upper)

    return ABBR_TO_STATE.get(abbr_upper)


def _lookup_special_state_mapping(text_clean: str) -> str | None:
    """Check special state mappings, guarding against country names."""
    if text_clean not in STATE_MAPPINGS:
        return None
    mapped = STATE_MAPPINGS[text_clean]
    if mapped is None or mapped in COUNTRY_NAMES_AS_STATES:
        return None
    return mapped


def _lookup_state_abbreviation(text_clean: str, country_hint: str | None) -> str | None:
    """Match two-letter uppercase abbreviation and expand it."""
    match = _STATE_ABBR_PATTERN.search(text_clean)
    if not match:
        return None
    state_abbr = match.group(1)
    return expand_state_abbreviation(state_abbr, country_hint)


def _match_full_state_name(text_clean: str) -> str | None:
    """Match text against known full state/province/region names."""
    if not text_clean or len(text_clean) <= 2:
        return None

    text_lower = text_clean.lower()
    all_known_states = (
        CANADIAN_PROVINCES
        | INDIAN_STATES
        | AUSTRALIAN_STATES
        | GERMAN_STATES
        | UK_REGIONS
        | US_STATES_FULL
        | FRENCH_REGIONS
        | ITALIAN_REGIONS
        | SPANISH_REGIONS
        | MEXICAN_STATES
        | BRAZILIAN_STATES
    )

    if text_lower in all_known_states:
        return text_clean.title()
    return None


def extract_state(text: str, country_hint: str | None = None) -> str | None:
    """Extract state from text using pre-compiled patterns and known state names.

    Note: This function extracts geographic regions that are sub-national (states, provinces).
    Countries like "UK", "Germany", etc. should NOT be extracted as states - they are countries.

    Args:
        text: Text to extract state from.
        country_hint: Optional country name to resolve ambiguous abbreviations.
    """
    if not text:
        return None

    text_clean = _strip_zip_code(text)

    mapped = _lookup_special_state_mapping(text_clean)
    if mapped is not None:
        return mapped

    abbreviated = _lookup_state_abbreviation(text_clean, country_hint)
    if abbreviated is not None:
        return abbreviated

    return _match_full_state_name(text_clean)


def infer_country_from_state(state: str | None) -> str | None:
    """Infer country from state/province name."""
    if not state:
        return None

    state_lower = state.lower()

    if state_lower in CANADIAN_PROVINCES:
        return COUNTRY_CANADA

    if state_lower in US_STATES_FULL:
        return COUNTRY_UNITED_STATES

    if state_lower in INDIAN_STATES:
        return COUNTRY_INDIA

    if state_lower in AUSTRALIAN_STATES:
        return COUNTRY_AUSTRALIA

    if state_lower in GERMAN_STATES:
        return COUNTRY_GERMANY

    return None


def normalize_state_name(state: str | None) -> str | None:
    """Normalize state name by fixing variations and accents.

    This ensures consistent state naming across the database.
    """
    if not state:
        return state

    # Strip whitespace
    state = state.strip()

    # Check for exact matches in mapping
    if state in STATE_MAPPINGS:
        return STATE_MAPPINGS[state]

    return state
