from __future__ import annotations

import json
from pathlib import Path

from pipeline.classification.mapping import CANONICAL_CATEGORIES, CATEGORY_MAPPING, INVALID_CATEGORIES
from pipeline.location.constants import COUNTRIES, COUNTRY_ALIASES, INVALID_CITY_PATTERN_STRINGS, STATE_MAPPINGS

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_location_constants_json_has_required_sections():
    path = PROJECT_ROOT / "pipeline" / "location" / "data" / "location_constants.json"
    data = json.loads(path.read_text())

    required = {
        "countries",
        "country_aliases",
        "countries_as_cities",
        "us_state_abbreviations",
        "states_as_cities",
        "us_state_to_abbr",
        "canadian_provinces",
        "canadian_province_abbreviations",
        "indian_states",
        "indian_state_abbr",
        "australian_states",
        "german_states",
        "uk_regions",
        "invalid_city_pattern_strings",
        "invalid_states",
        "cities_as_states",
        "countries_as_states",
        "state_mappings",
    }

    assert required <= set(data)
    assert len(COUNTRIES) >= 150
    assert COUNTRY_ALIASES["usa"] == "United States"
    assert STATE_MAPPINGS["Washington D.C."] == "District of Columbia"
    assert INVALID_CITY_PATTERN_STRINGS


def test_category_mapping_json_targets_valid_canonical_categories():
    path = PROJECT_ROOT / "pipeline" / "data" / "category_mapping.json"
    data = json.loads(path.read_text())

    assert data["canonical_categories"] == CANONICAL_CATEGORIES
    assert set(data["invalid_categories"]) == INVALID_CATEGORIES
    assert CATEGORY_MAPPING

    canonical = set(CANONICAL_CATEGORIES)
    invalid_targets = {
        alias: target for alias, target in CATEGORY_MAPPING.items() if target is not None and target not in canonical
    }
    assert invalid_targets == {}
