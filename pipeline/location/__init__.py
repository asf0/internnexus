"""Location normalization module.

Provides comprehensive location parsing with support for:
- City, state, country extraction
- Region codes (APAC, EMEA, LATAM, etc.)
- Multi-location handling
- Remote/Hybrid/On-site detection
- Abbreviation expansion
"""

from pipeline.location.simple_parser import normalize_location
from pipeline.location.regions import (
    COUNTRY_TO_REGION,
    REGION_CODES,
    get_countries_for_region,
    get_region_for_country,
    is_region_code,
    normalize_region_code,
)


def clean_location(location: str | None) -> dict:
    """Alias for normalize_location for backward compatibility."""
    result = normalize_location(location)
    return {
        "location": result.get("full"),
        "city": result.get("city"),
        "state": result.get("state"),
        "country": result.get("country"),
    }


__all__ = [
    "normalize_location",
    "clean_location",
    "REGION_CODES",
    "COUNTRY_TO_REGION",
    "get_region_for_country",
    "get_countries_for_region",
    "is_region_code",
    "normalize_region_code",
]
