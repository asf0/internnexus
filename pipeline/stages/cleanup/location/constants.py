"""Geographic constants for location parsing and cleanup.

Static lookup data lives in ``pipeline/location/data/location_constants.json`` so
it can be reviewed and extended without editing parser code. This module keeps
backward-compatible constant names for existing pipeline imports.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Final, Pattern

COUNTRY_UNITED_STATES: Final[str] = "United States"
COUNTRY_UNITED_KINGDOM: Final[str] = "United Kingdom"
COUNTRY_SOUTH_KOREA: Final[str] = "South Korea"
COUNTRY_TURKEY: Final[str] = "Turkey"
COUNTRY_CZECHIA: Final[str] = "Czechia"
COUNTRY_INDIA: Final[str] = "India"
COUNTRY_GERMANY: Final[str] = "Germany"
COUNTRY_FRANCE: Final[str] = "France"
COUNTRY_CHINA: Final[str] = "China"
COUNTRY_JAPAN: Final[str] = "Japan"
COUNTRY_CANADA: Final[str] = "Canada"
COUNTRY_AUSTRALIA: Final[str] = "Australia"
COUNTRY_NETHERLANDS: Final[str] = "Netherlands"
COUNTRY_UAE: Final[str] = "United Arab Emirates"

_DATA_PATH = Path(__file__).with_name("data") / "location_constants.json"


@lru_cache(maxsize=1)
def _load_data() -> dict[str, Any]:
    with _DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _required(name: str) -> Any:
    data = _load_data()
    if name not in data:
        raise KeyError(f"Missing location constant data key: {name}")
    return data[name]


def _frozenset(name: str) -> frozenset[str]:
    return frozenset(_required(name))


def _dict(name: str) -> dict[str, Any]:
    return dict(_required(name))


def _compiled_pattern_pairs(name: str) -> list[tuple[Pattern[str], str]]:
    data = _required(name)
    return [(re.compile(pair["pattern"], re.IGNORECASE), pair["country"]) for pair in data]


COUNTRIES: Final[frozenset[str]] = _frozenset("countries")
COUNTRY_ALIASES: Final[dict[str, str]] = _dict("country_aliases")
COUNTRIES_AS_CITIES: Final[frozenset[str]] = _frozenset("countries_as_cities")
US_STATE_ABBREVIATIONS: Final[frozenset[str]] = _frozenset("us_state_abbreviations")
STATES_AS_CITIES: Final[frozenset[str]] = _frozenset("states_as_cities")
US_STATE_TO_ABBR: Final[dict[str, str]] = _dict("us_state_to_abbr")
CANADIAN_PROVINCES: Final[frozenset[str]] = _frozenset("canadian_provinces")
CANADIAN_PROVINCE_ABBREVIATIONS: Final[dict[str, str]] = _dict("canadian_province_abbreviations")
INDIAN_STATES: Final[frozenset[str]] = _frozenset("indian_states")
INDIAN_STATE_ABBR: Final[dict[str, str]] = _dict("indian_state_abbr")
AUSTRALIAN_STATES: Final[frozenset[str]] = _frozenset("australian_states")
GERMAN_STATES: Final[frozenset[str]] = _frozenset("german_states")
UK_REGIONS: Final[frozenset[str]] = _frozenset("uk_regions")
INVALID_CITY_PATTERN_STRINGS: Final[list[str]] = list(_required("invalid_city_pattern_strings"))
INVALID_CITY_PATTERNS: Final[list[Pattern[str]]] = [
    re.compile(pattern, re.IGNORECASE) for pattern in INVALID_CITY_PATTERN_STRINGS
]
INVALID_STATES: Final[frozenset[str]] = _frozenset("invalid_states")
CITIES_AS_STATES: Final[dict[str, str]] = _dict("cities_as_states")
COUNTRIES_AS_STATES: Final[dict[str, str]] = _dict("countries_as_states")
STATE_MAPPINGS: Final[dict[str, str | None]] = _dict("state_mappings")
COUNTRY_PATTERN_PAIRS: Final[list[tuple[Pattern[str], str]]] = _compiled_pattern_pairs("country_pattern_pairs")
COUNTRY_ABBR_PATTERN_PAIRS: Final[list[tuple[Pattern[str], str]]] = _compiled_pattern_pairs(
    "country_abbr_pattern_pairs"
)
COUNTRY_ABBREV_FULL_MATCH: Final[dict[str, str]] = _dict("country_abbrev_full_match")
US_STATES_FULL: Final[frozenset[str]] = _frozenset("us_states_full")
FRENCH_REGIONS: Final[frozenset[str]] = _frozenset("french_regions")
ITALIAN_REGIONS: Final[frozenset[str]] = _frozenset("italian_regions")
SPANISH_REGIONS: Final[frozenset[str]] = _frozenset("spanish_regions")
MEXICAN_STATES: Final[frozenset[str]] = _frozenset("mexican_states")
BRAZILIAN_STATES: Final[frozenset[str]] = _frozenset("brazilian_states")
COUNTRY_NAMES_AS_STATES: Final[frozenset[str]] = _frozenset("country_names_as_states")
SINGLE_PART_COUNTRY_NAMES: Final[frozenset[str]] = _frozenset("single_part_country_names")
MAJOR_CITY_STATE_NAMES: Final[frozenset[str]] = _frozenset("major_city_state_names")

ABBR_TO_STATE: Final[dict[str, str]] = {
    **{abbr: state for state, abbr in US_STATE_TO_ABBR.items()},
    **CANADIAN_PROVINCE_ABBREVIATIONS,
}
US_CITIES: Final[frozenset[str]] = frozenset(_required("us_cities"))
INTERNATIONAL_CITIES: Final[dict[str, str]] = _dict("international_cities")
