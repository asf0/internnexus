"""Unified location normalization module using geostring library.

This module provides a single source of truth for location parsing and normalization
across the ingestion pipeline. It uses the geostring library for accurate geocoding
with custom logic for handling edge cases like Remote, Hybrid, and street addresses.
"""

from __future__ import annotations

import logging
import re
import warnings

import pycountry

logger = logging.getLogger(__name__)

with warnings.catch_warnings():
    warnings.simplefilter("ignore", SyntaxWarning)
    import geostring as geo

REMOTE_PATTERNS = [
    r"^remote\s*[-–]?\s*(us|usa|united states)?$",
    r"^us\s*[-–]?\s*remote$",
    r"^remote\s+us$",
    r"^remote\s+usa$",
    r"^remote\s+united\s+states$",
    r"^remote\s+canada$",
    r"^remote\s+uk$",
    r"^remote\s*\([^\)]*\)$",
    r"^remote\s*$",
]

HYBRID_PATTERNS = [
    r"^hybrid\s*[-–]?\s*(remote)?(\s+(us|usa))?$",
    r"^hybrid\s*$",
]

STREET_ADDRESS_PATTERNS = [
    r"^\d+\s+(street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd|parkway|pkwy|way|court|ct|place|pl)",
    r"^\d+\s+[a-z]+(\s+[a-z]+)?\s+(st|ave|rd|dr|ln|blvd|pkwy|way|ct|pl)[\s,\.]",
]

CA_CITIES = {
    "san francisco",
    "los angeles",
    "palo alto",
    "mountain view",
    "hawthorne",
    "long beach",
    "san jose",
    "sunnyvale",
    "menlo park",
    "redwood city",
    "oakland",
    "berkeley",
    "sacramento",
    "pasadena",
    "santa monica",
    "burbank",
    "glendale",
    "irvine",
    "valencia",
    "anaheim",
    "fremont",
    "san diego",
    "san mateo",
    "cupertino",
    "santa clara",
    "campbell",
    "milpitas",
    "daly city",
    "san leandro",
    "hayward",
    "foster city",
    "belmont",
    "san carlos",
    "redwood shores",
    "emeryville",
    "alameda",
    "dublin",
    "pleasanton",
    "livermore",
    "walnut creek",
    "concord",
    "los altos",
    "los gatos",
    "saratoga",
    "santa cruz",
    "monterey",
    "beverly hills",
    "malibu",
    "venice",
    "santa barbara",
    "bakersfield",
    "fresno",
    "modesto",
    "stockton",
    "richmond",
    "vallejo",
    "fairfield",
    "vacaville",
    "ventura",
    "oxnard",
    "simi valley",
    "thousand oaks",
    "torrance",
    "inglewood",
    "compton",
    "carson",
    "norwalk",
    "downey",
    "whittier",
    "el monte",
    "west covina",
    "pomona",
    "riverside",
    "san bernardino",
    "ontario",
    "fontana",
    "rancho cucamonga",
    "moreno valley",
    "corona",
    "palmdale",
    "lancaster",
    "santa clarita",
    "van nuys",
    "woodland hills",
}

UK_CITIES = {
    "london",
    "manchester",
    "birmingham",
    "leeds",
    "glasgow",
    "liverpool",
    "edinburgh",
    "bristol",
    "sheffield",
    "newcastle",
    "nottingham",
    "brighton",
    "cambridge",
    "oxford",
    "belfast",
    "cardiff",
    "southampton",
    "leicester",
    "coventry",
    "hull",
    "reading",
    "bournemouth",
    "exeter",
    "bath",
    "york",
}


def _get_us_state_abbreviations() -> set[str]:
    """Get US state abbreviations from pycountry."""
    us_subdivisions = pycountry.subdivisions.get(country_code="US")
    return {sub.code.split("-")[1] for sub in us_subdivisions}


def _get_us_state_names() -> set[str]:
    """Get US state names from pycountry."""
    us_subdivisions = pycountry.subdivisions.get(country_code="US")
    return {sub.name.lower() for sub in us_subdivisions}


def _get_state_abbr_to_name() -> dict[str, str]:
    """Get mapping of US state abbreviation to full name from pycountry."""
    us_subdivisions = pycountry.subdivisions.get(country_code="US")
    return {sub.code.split("-")[1]: sub.name for sub in us_subdivisions}


def _get_country_lookup() -> dict[str, str]:
    """Build a lookup dict for country name/code to standardized name."""
    lookup = {}
    for country in pycountry.countries:
        name = country.name
        lookup[name.lower()] = name
        if hasattr(country, "official_name"):
            lookup[country.official_name.lower()] = name
        if hasattr(country, "common_name"):
            lookup[country.common_name.lower()] = name
        lookup[country.alpha_2.lower()] = name
        lookup[country.alpha_3.lower()] = name
    lookup["usa"] = "United States"
    lookup["us"] = "United States"
    lookup["u.s."] = "United States"
    lookup["u.s.a."] = "United States"
    lookup["uk"] = "United Kingdom"
    lookup["u.k."] = "United Kingdom"
    lookup["great britain"] = "United Kingdom"
    lookup["england"] = "United Kingdom"
    lookup["scotland"] = "United Kingdom"
    lookup["wales"] = "United Kingdom"
    return lookup


US_STATE_ABBR = _get_us_state_abbreviations()
US_STATE_NAMES = _get_us_state_names()
STATE_ABBR_TO_NAME = _get_state_abbr_to_name()
COUNTRY_ALIASES = _get_country_lookup()


def _is_remote_or_hybrid(location: str) -> str | None:
    """Check if location is Remote or Hybrid pattern."""
    loc_lower = location.lower().strip()
    for pattern in REMOTE_PATTERNS:
        if re.match(pattern, loc_lower, re.IGNORECASE):
            return "Remote"
    for pattern in HYBRID_PATTERNS:
        if re.match(pattern, loc_lower, re.IGNORECASE):
            return "Hybrid"
    return None


def _is_street_address(location: str) -> bool:
    """Check if location looks like a street address."""
    loc_lower = location.lower().strip()
    for pattern in STREET_ADDRESS_PATTERNS:
        if re.match(pattern, loc_lower, re.IGNORECASE):
            return True
    return False


def _is_ca_city(location: str) -> bool:
    """Check if location contains a known California city."""
    loc_lower = location.lower().strip()
    for city in CA_CITIES:
        if city in loc_lower:
            return True
    return False


def _is_uk_city(location: str) -> bool:
    """Check if location contains a known UK city."""
    loc_lower = location.lower().strip()
    for city in UK_CITIES:
        if city in loc_lower:
            return True
    return False


def _extract_state_abbreviation(location: str) -> str | None:
    """Extract US state abbreviation from location if present."""
    parts = re.split(r"[,\s]+", location.upper())
    for part in parts:
        if part in US_STATE_ABBR:
            return part
    return None


def _disambiguate_geostring_result(
    result: dict, original_location: str
) -> tuple[str | None, str | None, str | None]:
    """Disambiguate geostring results with '?' separators.

    Returns (city, state, country) tuple.
    """
    city_raw = result.get("resolved_city", "")
    state_raw = result.get("resolved_subcountry", "")
    country_raw = result.get("resolved_country", "")

    city = None
    state = None
    country = None

    if city_raw and "?" not in city_raw:
        city = city_raw.title()
    elif city_raw and "?" in city_raw:
        parts = city_raw.split("?")
        city = parts[0].title()

    if state_raw and "?" not in state_raw:
        state = state_raw.title()
    elif state_raw and "?" in state_raw:
        parts = state_raw.split("?")
        if _is_ca_city(original_location):
            for p in parts:
                p_lower = p.lower().strip()
                if p_lower == "california":
                    state = "California"
                    country = "United States"
                    break
            if not state:
                state = parts[0].title()
        elif _is_uk_city(original_location):
            uk_regions = ["england", "scotland", "wales", "northern ireland"]
            for p in parts:
                p_lower = p.lower().strip()
                if p_lower in uk_regions:
                    state = p.title()
                    country = "United Kingdom"
                    break
            if not state:
                state = parts[0].title()
        else:
            state = parts[0].title()

    if country_raw and "?" not in country_raw:
        country = country_raw.title()
    elif country_raw and "?" in country_raw:
        parts = country_raw.split("?")
        if _is_ca_city(original_location):
            for p in parts:
                p_lower = p.lower().strip()
                if p_lower == "united states":
                    country = "United States"
                    break
            if not country:
                country = parts[0].title()
        elif _is_uk_city(original_location):
            for p in parts:
                p_lower = p.lower().strip()
                if p_lower == "united kingdom":
                    country = "United Kingdom"
                    break
            if not country:
                country = parts[0].title()
        else:
            country = parts[0].title()

    return city, state, country


def _simple_parse(location: str) -> tuple[str | None, str | None, str | None]:
    """Simple parsing for when geostring returns empty."""
    parts = [p.strip() for p in re.split(r"[,;]+", location) if p.strip()]

    city = None
    state = None
    country = None

    state_abbr = _extract_state_abbreviation(location)
    if state_abbr:
        state = STATE_ABBR_TO_NAME.get(state_abbr)
        country = "United States"
        for part in parts:
            part_lower = part.lower().strip()
            if part_lower not in US_STATE_ABBR and part_lower not in US_STATE_NAMES:
                if len(part) > 2 and part_lower not in COUNTRY_ALIASES:
                    city = part.title()
                    break
        return city, state, country

    for part in parts:
        part_lower = part.lower().strip()
        if part_lower in COUNTRY_ALIASES:
            country = COUNTRY_ALIASES[part_lower]
        elif part_lower in US_STATE_NAMES:
            state = part.title()
            country = "United States"
        elif part.upper() in US_STATE_ABBR:
            state = STATE_ABBR_TO_NAME.get(part.upper())
            country = "United States"
        elif not city and len(part) > 1:
            city = part.title()

    return city, state, country


def normalize_location(location: str | None) -> dict:
    """Normalize location string into city, state, country components.

    Args:
        location: Raw location string from job posting

    Returns:
        Dict with keys:
        - 'full': Normalized full location string
        - 'city': City name or None
        - 'state': State/province name or None
        - 'country': Country name or None
    """
    if not location or not location.strip():
        return {"full": None, "city": None, "state": None, "country": None}

    location = location.strip()

    if len(location) > 150:
        return {"full": None, "city": None, "state": None, "country": None}

    special_type = _is_remote_or_hybrid(location)
    if special_type:
        return {"full": special_type, "city": None, "state": None, "country": None}

    if _is_street_address(location):
        return {"full": None, "city": None, "state": None, "country": None}

    street_prefix_pattern = r"^(\d+\s+[a-zA-Z0-9\s]+?(street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd|parkway|pkwy|way|court|ct|place|pl|circle|cir|trail|trl|highway|hwy|freeway|fwy)[,\s]*)"
    location = re.sub(street_prefix_pattern, "", location, flags=re.IGNORECASE).strip()
    location = re.sub(r"^\d+\s+[a-zA-Z]+[,\s]+", "", location).strip()
    if not location:
        return {"full": None, "city": None, "state": None, "country": None}

    skip_patterns = [
        "add location here",
        "tbd",
        "varies",
        "multiple",
        "unknown",
        "any location",
        "any",
        "various",
        "see description",
    ]
    if location.lower() in skip_patterns:
        return {"full": None, "city": None, "state": None, "country": None}

    match = re.search(r"\(\(([^)]+)\)\)", location)
    if match:
        location = match.group(1).strip()
    else:
        loc_result = re.sub(r"\([^)]*\)", "", location)
        location = loc_result.strip() if loc_result else ""

    location = re.sub(r"[/\\|]+", " ", location)  # type: ignore[arg-type]
    location = re.sub(r"\s*-\s*", ", ", location)  # type: ignore[arg-type]
    location = re.sub(r"\s+", " ", location).strip()  # type: ignore[arg-type]

    if not location:
        return {"full": None, "city": None, "state": None, "country": None}

    if re.match(r"^\d+", location):
        parts = [p.strip() for p in location.split(",")]
        for i in range(len(parts) - 1, -1, -1):
            part = parts[i]
            state_match = re.search(r"\b([A-Z]{2})\b", part)
            if state_match:
                state_clean = re.sub(r"\s+\d{5}(?:-\d{4})?$", "", part).strip()
                city_part = ""
                for j in range(i - 1, -1, -1):
                    part_j = parts[j]
                    if re.search(
                        r"\b(suite|ste|unit|apt|apartment|#|floor|fl)\b", part_j, re.IGNORECASE
                    ):
                        continue
                    is_street = re.match(r"^\d+", part_j) or re.search(
                        r"\b(street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd|parkway|pkwy|way|highway|hwy|circle|cir|trail|trl|court|ct|plaza|plz|terrace|ter|pike)\b",
                        part_j,
                        re.IGNORECASE,
                    )
                    if is_street:
                        words = part_j.split()
                        if len(words) > 1 and not city_part:
                            potential_city = words[-1]
                            if potential_city.lower() in CA_CITIES or not re.search(
                                r"\b(drive|dr|road|rd|street|st|avenue|ave|lane|ln|way|court|ct|circle|cir|trail|trl|parkway|pkwy|boulevard|blvd|highway|hwy|plaza|plz|terrace|ter|pike)\b",
                                potential_city,
                                re.IGNORECASE,
                            ):
                                city_part = potential_city
                        continue
                    city_part = part_j
                    break
                location = f"{city_part}, {state_clean}" if city_part else state_clean
                break
            elif i == len(parts) - 2 and len(parts) >= 2:
                location = f"{parts[i]}, {parts[i + 1]}"
                break

    if ";" in location:
        location = location.split(";")[0].strip()

    if not location or len(location) < 2:
        return {"full": None, "city": None, "state": None, "country": None}

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            result = geo.resolve(location)

        if result and (result.get("resolved_city") or result.get("resolved_country")):
            city, state, country = _disambiguate_geostring_result(result, location)

            if not city and not state and not country:
                city, state, country = _simple_parse(location)
        else:
            city, state, country = _simple_parse(location)
    except Exception as e:
        logger.debug(f"geostring failed for '{location}': {e}")
        city, state, country = _simple_parse(location)

    if state and state.lower() in US_STATE_NAMES and not country:
        country = "United States"

    if city and not state and not country:
        city_lower = city.lower()
        if city_lower in CA_CITIES:
            state = "California"
            country = "United States"
        elif city_lower in UK_CITIES:
            country = "United Kingdom"

    loc_parts = []
    if city:
        loc_parts.append(city)
    if state:
        loc_parts.append(state)
    if country:
        loc_parts.append(country)

    full_location = ", ".join(loc_parts) if loc_parts else location

    return {
        "full": full_location,
        "city": city,
        "state": state,
        "country": country,
    }


def clean_location(location: str | None) -> dict:
    """Alias for normalize_location for backward compatibility with cleanup.py."""
    result = normalize_location(location)
    return {
        "location": result["full"],
        "city": result["city"],
        "state": result["state"],
        "country": result["country"],
    }
