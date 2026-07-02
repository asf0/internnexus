"""Backwards-compat shim.

New code should import from the focused submodules (country_parser,
state_parser, city_parser, normalize) directly. This module is preserved
so existing callers - notably ``pipeline/cleanup/`` - keep their imports
intact until the cleanup refactor re-routes them.
"""

from __future__ import annotations

from pipeline.location.country_parser import (
    _normalize_country_name,  # noqa: F401
    _strip_region_codes,  # noqa: F401
    extract_country_from_text,
)
from pipeline.location.state_parser import (
    expand_state_abbreviation,
    extract_state,
    infer_country_from_state,
    normalize_state_name,
)
from pipeline.location.city_parser import (
    clean_city_name,
    extract_city_before_state,
    extract_city_from_street_address,
    infer_country_from_city,
    is_fake_city,
    is_street_address,
)
from pipeline.location.normalize import (
    has_multiple_remote_locations,
    is_remote_pattern,
    normalize_location,
)

__all__ = [
    "normalize_location",
    "normalize_state_name",
    "extract_state",
    "extract_country_from_text",
    "infer_country_from_city",
    "is_fake_city",
    "is_street_address",
    "clean_city_name",
    "expand_state_abbreviation",
    "infer_country_from_state",
    "extract_city_from_street_address",
    "extract_city_before_state",
    "has_multiple_remote_locations",
    "is_remote_pattern",
]
