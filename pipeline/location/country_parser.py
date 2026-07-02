"""Country extraction from free-text location strings."""

from __future__ import annotations

import re

from pipeline.location._patterns import _REGION_CODE_PATTERN
from pipeline.location.constants import (
    COUNTRY_ABBREV_FULL_MATCH,
    COUNTRY_ABBR_PATTERN_PAIRS,
    COUNTRY_ALIASES,
    COUNTRY_PATTERN_PAIRS,
    COUNTRY_UNITED_STATES,
)


def _normalize_country_name(country: str) -> str:
    """Normalize country name by expanding abbreviations and aliases."""
    if not country:
        return country

    # Strip whitespace
    country = country.strip()
    country_lower = country.lower()

    # Check for abbreviation full matches (US, U.S, GB, IN, etc.)
    if country_lower in COUNTRY_ABBREV_FULL_MATCH:
        return COUNTRY_ABBREV_FULL_MATCH[country_lower]

    # Check for aliases (alternative names)
    if country_lower in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[country_lower]

    return country


def _strip_region_codes(text: str) -> str:
    """Strip region codes like EMEA, AMER, APAC from end of text."""
    return _REGION_CODE_PATTERN.sub("", text).strip()


def extract_country_from_text(text: str) -> str | None:
    """Extract country from text using pre-compiled word boundary patterns.

    Improvements:
    - Expands abbreviations (US -> United States)
    - Normalizes alternative names (Türkiye -> Turkey)
    - Strips region codes (Germany, EMEA -> Germany)
    - Handles trailing spaces
    """
    if not text:
        return None

    # Strip region codes first
    text = _strip_region_codes(text)
    text_lower = text.lower().strip()

    # Check for abbreviation full matches first (exact match only)
    if text_lower in COUNTRY_ABBREV_FULL_MATCH:
        return COUNTRY_ABBREV_FULL_MATCH[text_lower]

    # Check for aliases (alternative country names)
    if text_lower in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[text_lower]

    # Handle special case: "U.S" or "U.S." within text (e.g., "Palo Alto, CA, U.S")
    if re.search(r"\bu\.s\.?\b", text_lower):
        return COUNTRY_UNITED_STATES

    # Check full country names using pre-compiled patterns
    for pattern, country in COUNTRY_PATTERN_PAIRS:
        if pattern.search(text_lower):
            return country

    # Check abbreviations using pre-compiled patterns (word boundary matches)
    for pattern, country in COUNTRY_ABBR_PATTERN_PAIRS:
        if pattern.search(text_lower):
            return country

    return None
