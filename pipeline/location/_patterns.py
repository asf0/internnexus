"""Pre-compiled regex patterns shared by location parsers."""

from __future__ import annotations

import re

# Street address detection
_STREET_NUMBER_PATTERN = re.compile(r"^\d+\s")

# Fake city detection
_FAKE_CITY_PATTERNS = [
    re.compile(r"\b" + indicator + r"\b", re.IGNORECASE)
    for indicator in [
        "remote",
        "hybrid",
        "zone",
        "region",
        "area",
        "various",
        "multiple",
        "distributed",
        "virtual",
        "anywhere",
        "any",
        "flexible",
        "tbd",
        "n/a",
        "unknown",
        "hub",
        "center",
        "office",
        "location",
        "suite",
        "apt",
        "unit",
        "building",
        "floor",
        "room",
        "plaza",
        "mall",
        "amer",
        "apac",
        "emea",
        "latam",
        "global",
        "eu",
        "europe",
    ]
]
_FAKE_CITY_PREFIX_PATTERN = re.compile(r"^(remote|zone|region)\s+\w+", re.IGNORECASE)

# Region code patterns (to strip from country)
_REGION_CODE_PATTERN = re.compile(r",?\s*(EMEA|AMER|APAC|LATAM)\s*$", re.IGNORECASE)

# Remote patterns
_REMOTE_PATTERNS = [
    re.compile(r"^remote$", re.IGNORECASE),
    re.compile(r"^remote\s+", re.IGNORECASE),
    re.compile(r"\s+remote$", re.IGNORECASE),
    re.compile(r"^remote\s*[-–,]", re.IGNORECASE),
    re.compile(r"[-–,]\s*remote", re.IGNORECASE),
]
_MULTI_LOC_DELIMITERS = re.compile(r"[;|]")

# Street extraction patterns
_STREET_TYPE_PATTERN = re.compile(
    r"^\d+\s+([NnSsEeWw]\.?\s+)?([A-Za-z]+\s+)?\b(st|street|ave|avenue|blvd|boulevard|dr\b|drive|rd|road|ln|lane|way|ct|court|pl|place|pkwy|parkway|trail|trl|cir|circle|bldg)\b[\s\.]*",
    re.IGNORECASE,
)
_SUITE_PATTERN = re.compile(r"\s+(suite|ste|apt|unit|#|lot)\s*[A-Za-z0-9\-]+", re.IGNORECASE)
_WHITESPACE_PATTERN = re.compile(r"\s+")

# City/state patterns
_CITY_STATE_PATTERN = re.compile(r"^([A-Za-z\s]+)\s+([A-Z]{2})$")
_STATE_ABBR_PATTERN = re.compile(r"\b([A-Z]{2})\b")
_CITY_SUFFIX_PATTERN = re.compile(r"\s+(City|Town|Village|Municipality)$", re.IGNORECASE)
_ZIP_PATTERN = re.compile(r"\s+\d{5}(-\d{4})?$")
_TRAILING_STATE_PATTERN = re.compile(r",?\s*[A-Z]{2}\s*$")
