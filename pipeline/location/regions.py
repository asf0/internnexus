"""Region code definitions for location filtering.

Provides mappings between region codes (APAC, EMEA, etc.) and their
component countries for search and filtering purposes.
"""

from __future__ import annotations

REGION_CODES: dict[str, dict] = {
    "NA": {
        "name": "North America",
        "aliases": ["NORTH AMERICA", "N AMERICA"],
        "countries": ["US", "CA", "MX"],
        "search_terms": ["north america", "na"],
    },
    "LATAM": {
        "name": "Latin America",
        "aliases": ["LATIN AMERICA", "LATIN AM", "LATIN"],
        "countries": ["BR", "AR", "CL", "CO", "PE", "MX", "EC", "UY", "PY", "BO", "VE"],
        "search_terms": ["latin america", "latam"],
    },
    "EMEA": {
        "name": "Europe, Middle East, Africa",
        "aliases": ["EUROPE MIDDLE EAST AFRICA"],
        "countries": [
            "GB",
            "DE",
            "FR",
            "NL",
            "BE",
            "CH",
            "AT",
            "ES",
            "IT",
            "PT",
            "PL",
            "SE",
            "NO",
            "DK",
            "FI",
            "IE",
            "ZA",
            "AE",
            "IL",
            "TR",
            "SA",
            "EG",
            "NG",
            "KE",
            "MA",
            "RU",
            "UA",
            "CZ",
            "RO",
            "HU",
            "GR",
        ],
        "search_terms": ["emea", "europe middle east africa"],
    },
    "APAC": {
        "name": "Asia-Pacific",
        "aliases": ["APJ", "ASIA PACIFIC", "ASIA-PACIFIC"],
        "countries": [
            "JP",
            "KR",
            "CN",
            "SG",
            "HK",
            "TW",
            "IN",
            "MY",
            "TH",
            "VN",
            "PH",
            "ID",
            "AU",
            "NZ",
        ],
        "search_terms": ["apac", "apj", "asia pacific", "asia-pacific"],
    },
    "DACH": {
        "name": "Germany, Austria, Switzerland",
        "aliases": [],
        "countries": ["DE", "AT", "CH"],
        "search_terms": ["dach"],
    },
    "Nordics": {
        "name": "Nordic Countries",
        "aliases": ["NORDIC", "SCANDINAVIA"],
        "countries": ["SE", "NO", "DK", "FI", "IS"],
        "search_terms": ["nordics", "nordic", "scandinavia"],
    },
    "Benelux": {
        "name": "Belgium, Netherlands, Luxembourg",
        "aliases": [],
        "countries": ["BE", "NL", "LU"],
        "search_terms": ["benelux"],
    },
}

COUNTRY_TO_REGION: dict[str, str] = {}
for code, data in REGION_CODES.items():
    for country in data["countries"]:
        COUNTRY_TO_REGION[country] = code


def get_region_for_country(country_code: str) -> str | None:
    """Get region code for a country code."""
    return COUNTRY_TO_REGION.get(country_code.upper())


def get_countries_for_region(region_code: str) -> list[str]:
    """Get list of country codes for a region code."""
    region = REGION_CODES.get(region_code.upper())
    return region["countries"] if region else []


def is_region_code(value: str) -> bool:
    """Check if a value is a valid region code or alias."""
    upper = value.upper()
    if upper in REGION_CODES:
        return True
    for code, data in REGION_CODES.items():
        if upper in data.get("aliases", []):
            return True
    return False


def normalize_region_code(value: str) -> str | None:
    """Normalize a region code or alias to the canonical code."""
    upper = value.upper()
    if upper in REGION_CODES:
        return upper
    for code, data in REGION_CODES.items():
        if upper in data.get("aliases", []):
            return code
    return None
