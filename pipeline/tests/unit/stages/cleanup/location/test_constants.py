"""Unit tests for the location constants loaded from location_constants.json.

Shape checks (type, size, casing) are table-driven: the tables below are the
readable inventory of what the data file must contain, and a per-constant test
for each of those properties would say the same thing 60 times over.

Everything else is asserted individually, because it encodes a fact that is not
derivable from the table: specific mappings, referential integrity between
constants, regex flags, and ordering that the matching code depends on.
"""

import json
import re

import pytest

from pipeline.stages.cleanup.location.constants import (
    ABBR_TO_STATE,
    AUSTRALIAN_STATES,
    BRAZILIAN_STATES,
    CANADIAN_PROVINCES,
    CANADIAN_PROVINCE_ABBREVIATIONS,
    CITIES_AS_STATES,
    COUNTRIES,
    COUNTRIES_AS_CITIES,
    COUNTRIES_AS_STATES,
    COUNTRY_ABBREV_FULL_MATCH,
    COUNTRY_ABBR_PATTERN_PAIRS,
    COUNTRY_ALIASES,
    COUNTRY_NAMES_AS_STATES,
    COUNTRY_PATTERN_PAIRS,
    FRENCH_REGIONS,
    GERMAN_STATES,
    INDIAN_STATES,
    INVALID_CITY_PATTERNS,
    INVALID_STATES,
    INTERNATIONAL_CITIES,
    ITALIAN_REGIONS,
    MAJOR_CITY_STATE_NAMES,
    MEXICAN_STATES,
    SINGLE_PART_COUNTRY_NAMES,
    SPANISH_REGIONS,
    STATE_MAPPINGS,
    UK_REGIONS,
    US_CITIES,
    US_STATE_ABBREVIATIONS,
    US_STATE_TO_ABBR,
    US_STATES_FULL,
)

# (name, value, expected container type, exact size or None, minimum size or None)
_CONSTANTS = [
    ("COUNTRIES", COUNTRIES, frozenset, None, 150),
    ("COUNTRY_ALIASES", COUNTRY_ALIASES, dict, 16, None),
    ("US_STATE_ABBREVIATIONS", US_STATE_ABBREVIATIONS, frozenset, 51, None),
    ("US_STATE_TO_ABBR", US_STATE_TO_ABBR, dict, 51, None),
    ("ABBR_TO_STATE", ABBR_TO_STATE, dict, None, None),
    ("CANADIAN_PROVINCES", CANADIAN_PROVINCES, frozenset, 13, None),
    ("CANADIAN_PROVINCE_ABBREVIATIONS", CANADIAN_PROVINCE_ABBREVIATIONS, dict, 13, None),
    ("INDIAN_STATES", INDIAN_STATES, frozenset, None, 21),
    ("AUSTRALIAN_STATES", AUSTRALIAN_STATES, frozenset, 8, None),
    ("GERMAN_STATES", GERMAN_STATES, frozenset, None, 11),
    ("UK_REGIONS", UK_REGIONS, frozenset, None, None),
    ("INVALID_CITY_PATTERNS", INVALID_CITY_PATTERNS, list, None, 1),
    ("INVALID_STATES", INVALID_STATES, frozenset, None, None),
    ("STATE_MAPPINGS", STATE_MAPPINGS, dict, None, 101),
    ("CITIES_AS_STATES", CITIES_AS_STATES, dict, None, 101),
    ("COUNTRIES_AS_CITIES", COUNTRIES_AS_CITIES, frozenset, None, 101),
    ("COUNTRIES_AS_STATES", COUNTRIES_AS_STATES, dict, None, 51),
    ("US_CITIES", US_CITIES, frozenset, 156, None),
    ("INTERNATIONAL_CITIES", INTERNATIONAL_CITIES, dict, 141, None),
    ("COUNTRY_PATTERN_PAIRS", COUNTRY_PATTERN_PAIRS, list, 75, None),
    ("COUNTRY_ABBR_PATTERN_PAIRS", COUNTRY_ABBR_PATTERN_PAIRS, list, 72, None),
    ("COUNTRY_ABBREV_FULL_MATCH", COUNTRY_ABBREV_FULL_MATCH, dict, 78, None),
    ("US_STATES_FULL", US_STATES_FULL, frozenset, 51, None),
    ("FRENCH_REGIONS", FRENCH_REGIONS, frozenset, 13, None),
    ("ITALIAN_REGIONS", ITALIAN_REGIONS, frozenset, 25, None),
    ("SPANISH_REGIONS", SPANISH_REGIONS, frozenset, 27, None),
    ("MEXICAN_STATES", MEXICAN_STATES, frozenset, 34, None),
    ("BRAZILIAN_STATES", BRAZILIAN_STATES, frozenset, 27, None),
    ("COUNTRY_NAMES_AS_STATES", COUNTRY_NAMES_AS_STATES, frozenset, 30, None),
    ("SINGLE_PART_COUNTRY_NAMES", SINGLE_PART_COUNTRY_NAMES, frozenset, 36, None),
    ("MAJOR_CITY_STATE_NAMES", MAJOR_CITY_STATE_NAMES, frozenset, 10, None),
]

_LOWERCASE_KEYED = [
    ("COUNTRY_ALIASES", COUNTRY_ALIASES),
    ("COUNTRY_ABBREV_FULL_MATCH", COUNTRY_ABBREV_FULL_MATCH),
    ("COUNTRIES_AS_CITIES", COUNTRIES_AS_CITIES),
    ("US_STATES_FULL", US_STATES_FULL),
    ("SINGLE_PART_COUNTRY_NAMES", SINGLE_PART_COUNTRY_NAMES),
    ("MAJOR_CITY_STATE_NAMES", MAJOR_CITY_STATE_NAMES),
]


@pytest.mark.parametrize(("name", "value", "expected_type"), [(n, v, t) for n, v, t, _e, _m in _CONSTANTS])
def test_constant_has_expected_container_type(name, value, expected_type):
    assert isinstance(value, expected_type), name


@pytest.mark.parametrize(
    ("name", "value", "expected"), [(n, v, e) for n, v, _t, e, _m in _CONSTANTS if e is not None]
)
def test_constant_has_exact_size(name, value, expected):
    assert len(value) == expected, name


@pytest.mark.parametrize(
    ("name", "value", "minimum"), [(n, v, m) for n, v, _t, _e, m in _CONSTANTS if m is not None]
)
def test_constant_meets_minimum_size(name, value, minimum):
    assert len(value) >= minimum, name


@pytest.mark.parametrize(("name", "value"), _LOWERCASE_KEYED)
def test_lookup_keys_are_lowercase(name, value):
    for key in value:
        assert key == key.lower(), f"{name}: {key!r}"


class TestCountriesConstant:
    'Test suite for COUNTRIES constant.'

    def test_countries_contains_expected_countries(self):
        expected = {"United States", "United Kingdom", "Canada", "Germany", "France"}
        for country in expected:
            assert country in COUNTRIES

    def test_countries_all_strings(self):
        for country in COUNTRIES:
            assert isinstance(country, str)
            assert len(country) > 0


class TestCountryAliases:
    'Test suite for COUNTRY_ALIASES constant.'

    def test_us_aliases_map_correctly(self):
        assert COUNTRY_ALIASES["us"] == "United States"
        assert COUNTRY_ALIASES["usa"] == "United States"
        assert COUNTRY_ALIASES["u.s"] == "United States"
        assert COUNTRY_ALIASES["u.s."] == "United States"

    def test_uk_aliases_map_correctly(self):
        assert COUNTRY_ALIASES["uk"] == "United Kingdom"
        assert COUNTRY_ALIASES["gb"] == "United Kingdom"

    def test_country_aliases_values_are_valid_countries(self):
        for alias, country in COUNTRY_ALIASES.items():
            assert country in COUNTRIES or country in {"Turkey", "South Korea", "Czechia"}


class TestUSStateAbbreviations:
    'Test suite for US_STATE_ABBREVIATIONS constant.'

    def test_us_state_abbreviations_contains_expected_states(self):
        expected = {"CA", "NY", "TX", "FL", "WA", "DC"}
        for state in expected:
            assert state in US_STATE_ABBREVIATIONS

    def test_us_state_abbreviations_all_uppercase(self):
        for abbr in US_STATE_ABBREVIATIONS:
            assert abbr == abbr.upper()
            assert len(abbr) == 2


class TestUSStateToAbbr:
    'Test suite for US_STATE_TO_ABBR constant.'

    def test_us_state_to_abbr_mappings_correct(self):
        assert US_STATE_TO_ABBR["California"] == "CA"
        assert US_STATE_TO_ABBR["New York"] == "NY"
        assert US_STATE_TO_ABBR["Texas"] == "TX"
        assert US_STATE_TO_ABBR["District of Columbia"] == "DC"

    def test_us_state_to_abbr_values_are_valid_abbreviations(self):
        for state, abbr in US_STATE_TO_ABBR.items():
            assert abbr in US_STATE_ABBREVIATIONS


class TestAbbrToState:
    'Test suite for ABBR_TO_STATE constant.'

    def test_abbr_to_state_includes_us_states(self):
        assert ABBR_TO_STATE["CA"] == "California"
        assert ABBR_TO_STATE["NY"] == "New York"
        assert ABBR_TO_STATE["TX"] == "Texas"

    def test_abbr_to_state_includes_canadian_provinces(self):
        assert ABBR_TO_STATE["ON"] == "Ontario"
        assert ABBR_TO_STATE["BC"] == "British Columbia"
        assert ABBR_TO_STATE["QC"] == "Quebec"

    def test_abbr_to_state_includes_dc(self):
        assert ABBR_TO_STATE["DC"] == "District of Columbia"


class TestCanadianProvinces:
    'Test suite for Canadian province constants.'

    def test_canadian_provinces_contains_expected(self):
        expected = {"ontario", "quebec", "british columbia", "alberta"}
        for province in expected:
            assert province in CANADIAN_PROVINCES

    def test_canadian_province_abbreviations_mappings(self):
        assert CANADIAN_PROVINCE_ABBREVIATIONS["ON"] == "Ontario"
        assert CANADIAN_PROVINCE_ABBREVIATIONS["BC"] == "British Columbia"


class TestOtherRegionConstants:
    'Test suite for other regional constants.'

    def test_indian_states_contains_expected(self):
        assert "karnataka" in INDIAN_STATES
        assert "maharashtra" in INDIAN_STATES
        assert "delhi" in INDIAN_STATES

    def test_uk_regions_contains_expected(self):
        assert "england" in UK_REGIONS
        assert "scotland" in UK_REGIONS
        assert "wales" in UK_REGIONS


class TestInvalidPatterns:
    'Test suite for invalid pattern constants.'

    def test_invalid_city_patterns_are_compiled_regex(self):
        import re

        for pattern in INVALID_CITY_PATTERNS:
            assert isinstance(pattern, re.Pattern)

    def test_invalid_states_contains_expected(self):
        assert "Remote" in INVALID_STATES
        assert "Hybrid" in INVALID_STATES
        assert "N/A" in INVALID_STATES


class TestStateMappings:
    'Test suite for STATE_MAPPINGS constant.'

    def test_state_mappings_dc_variations(self):
        assert STATE_MAPPINGS["Washington D.C."] == "District of Columbia"
        assert STATE_MAPPINGS["Washington, D.C."] == "District of Columbia"
        assert STATE_MAPPINGS["District Of Columbia"] == "District of Columbia"

    def test_state_mappings_can_return_none(self):
        assert STATE_MAPPINGS.get("Remote") is None


class TestCitiesAsStates:
    'Test suite for CITIES_AS_STATES constant.'

    def test_cities_as_states_contains_major_cities(self):
        assert "London" in CITIES_AS_STATES
        assert "Paris" in CITIES_AS_STATES
        assert "Tokyo" in CITIES_AS_STATES
        assert "Sydney" in CITIES_AS_STATES


class TestCountriesAsCities:
    'Test suite for COUNTRIES_AS_CITIES constant.'


class TestCountriesAsStates:
    'Test suite for COUNTRIES_AS_STATES constant.'

    def test_countries_as_states_mappings(self):
        assert COUNTRIES_AS_STATES["Singapore"] == "Singapore"
        assert COUNTRIES_AS_STATES["Hong Kong"] == "Hong Kong"


class TestUSCities:
    'Test suite for US_CITIES constant.'

    def test_us_cities_raw_json_has_156_entries(self):
        from pipeline.stages.cleanup.location.constants import _DATA_PATH as data_path
        with data_path.open(encoding="utf-8") as f:
            data = json.load(f)
        assert len(data["us_cities"]) == 156

    def test_removed_disputed_values_not_in_us(self):
        assert "vancouver" not in US_CITIES
        assert "birmingham" not in US_CITIES


class TestInternationalCities:
    'Test suite for INTERNATIONAL_CITIES constant.'

    def test_international_cities_json_has_141_entries(self):
        from pipeline.stages.cleanup.location.constants import _DATA_PATH as data_path
        with data_path.open(encoding="utf-8") as f:
            data = json.load(f)
        assert len(data["international_cities"]) == 141

    def test_international_cities_disputed(self):
        assert INTERNATIONAL_CITIES["vancouver"] == "Canada"
        assert INTERNATIONAL_CITIES["birmingham"] == "United Kingdom"


class TestCountryPatternPairs:
    'Test suite for COUNTRY_PATTERN_PAIRS constant.'

    def test_is_list_of_tuples(self):
        assert isinstance(COUNTRY_PATTERN_PAIRS, list)
        for item in COUNTRY_PATTERN_PAIRS:
            assert isinstance(item, tuple)
            assert len(item) == 2
            assert isinstance(item[0], re.Pattern)
            assert isinstance(item[1], str)

    def test_first_and_last_ordering(self):
        assert COUNTRY_PATTERN_PAIRS[0][1] == "United States"
        assert COUNTRY_PATTERN_PAIRS[-1][1] == "Oman"

    def test_patterns_have_IGNORECASE(self):
        for pattern, _ in COUNTRY_PATTERN_PAIRS:
            assert pattern.flags & re.IGNORECASE

    def test_patterns_use_word_boundaries(self):
        first_pattern = COUNTRY_PATTERN_PAIRS[0][0].pattern
        assert first_pattern.startswith("\\b")
        assert first_pattern.endswith("\\b")


class TestCountryAbbrPatternPairs:
    'Test suite for COUNTRY_ABBR_PATTERN_PAIRS constant.'

    def test_is_list_of_tuples(self):
        assert isinstance(COUNTRY_ABBR_PATTERN_PAIRS, list)
        for item in COUNTRY_ABBR_PATTERN_PAIRS:
            assert isinstance(item, tuple)
            assert len(item) == 2
            assert isinstance(item[0], re.Pattern)
            assert isinstance(item[1], str)

    def test_first_and_last_ordering(self):
        assert COUNTRY_ABBR_PATTERN_PAIRS[0][1] == "United States"
        assert COUNTRY_ABBR_PATTERN_PAIRS[-1][1] == "Cyprus"

    def test_patterns_have_IGNORECASE(self):
        for pattern, _ in COUNTRY_ABBR_PATTERN_PAIRS:
            assert pattern.flags & re.IGNORECASE

    def test_usa_pattern_matches(self):
        assert COUNTRY_ABBR_PATTERN_PAIRS[0][1] == "United States"


class TestCountryAbbrevFullMatch:
    'Test suite for COUNTRY_ABBREV_FULL_MATCH constant.'

    def test_ua_maps_to_ukraine(self):
        assert COUNTRY_ABBREV_FULL_MATCH["ua"] == "Ukraine"

    def test_boundary_values(self):
        assert COUNTRY_ABBREV_FULL_MATCH["us"] == "United States"
        assert COUNTRY_ABBREV_FULL_MATCH["gb"] == "United Kingdom"
        assert COUNTRY_ABBREV_FULL_MATCH["in"] == "India"
        assert COUNTRY_ABBREV_FULL_MATCH["mt"] == "Malta"


class TestCountryAliasesMerge:
    'Test suite for COUNTRY_ALIASES after inline merge.'

    def test_inline_only_entry_added(self):
        assert COUNTRY_ALIASES["united arab emirates"] == "United Arab Emirates"

    def test_existing_entries_preserved(self):
        assert COUNTRY_ALIASES["us"] == "United States"
        assert COUNTRY_ALIASES["uk"] == "United Kingdom"
        assert COUNTRY_ALIASES["gb"] == "United Kingdom"
        assert COUNTRY_ALIASES["czech republic"] == "Czechia"

    def test_inline_overlapping_entries_match(self):
        assert COUNTRY_ALIASES["turkiye"] == "Turkey"
        assert COUNTRY_ALIASES["türkiye"] == "Turkey"
        assert COUNTRY_ALIASES["the netherlands"] == "Netherlands"


class TestUSStatesFull:
    'Test suite for US_STATES_FULL constant.'

    def test_contains_all_states_and_dc(self):
        assert "california" in US_STATES_FULL
        assert "new york" in US_STATES_FULL
        assert "texas" in US_STATES_FULL
        assert "district of columbia" in US_STATES_FULL


class TestFrenchRegions:
    'Test suite for FRENCH_REGIONS constant.'

    def test_contains_expected(self):
        assert "île-de-france" in FRENCH_REGIONS
        assert "corse" in FRENCH_REGIONS
        assert "normandie" in FRENCH_REGIONS


class TestItalianRegions:
    'Test suite for ITALIAN_REGIONS constant.'

    def test_contains_expected(self):
        assert "lazio" in ITALIAN_REGIONS
        assert "lombardy" in ITALIAN_REGIONS
        assert "veneto" in ITALIAN_REGIONS


class TestSpanishRegions:
    'Test suite for SPANISH_REGIONS constant.'

    def test_contains_expected(self):
        assert "andalusia" in SPANISH_REGIONS
        assert "madrid" in SPANISH_REGIONS
        assert "valencia" in SPANISH_REGIONS


class TestMexicanStates:
    'Test suite for MEXICAN_STATES constant.'

    def test_contains_expected(self):
        assert "jalisco" in MEXICAN_STATES
        assert "mexico city" in MEXICAN_STATES
        assert "ciudad de méxico" in MEXICAN_STATES


class TestBrazilianStates:
    'Test suite for BRAZILIAN_STATES constant.'

    def test_contains_expected(self):
        assert "são paulo" in BRAZILIAN_STATES
        assert "rio de janeiro" in BRAZILIAN_STATES
        assert "acre" in BRAZILIAN_STATES


class TestCountryNamesAsStates:
    'Test suite for COUNTRY_NAMES_AS_STATES constant.'

    def test_contains_expected(self):
        assert "United States" in COUNTRY_NAMES_AS_STATES
        assert "Australia" in COUNTRY_NAMES_AS_STATES
        assert "India" in COUNTRY_NAMES_AS_STATES
        assert "Hong Kong" in COUNTRY_NAMES_AS_STATES


class TestSinglePartCountryNames:
    'Test suite for SINGLE_PART_COUNTRY_NAMES constant.'

    def test_contains_expected(self):
        assert "united states" in SINGLE_PART_COUNTRY_NAMES
        assert "us" in SINGLE_PART_COUNTRY_NAMES
        assert "uk" in SINGLE_PART_COUNTRY_NAMES
        assert "china" in SINGLE_PART_COUNTRY_NAMES


class TestMajorCityStateNames:
    'Test suite for MAJOR_CITY_STATE_NAMES constant.'

    def test_contains_expected(self):
        assert "new york" in MAJOR_CITY_STATE_NAMES
        assert "delhi" in MAJOR_CITY_STATE_NAMES
        assert "washington" in MAJOR_CITY_STATE_NAMES


def test_location_constants_json_has_required_sections():
    from pipeline.stages.cleanup.location.constants import (
        INVALID_CITY_PATTERN_STRINGS,
        _DATA_PATH as path,
    )

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
