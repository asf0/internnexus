"""Unit tests for pipeline/location/constants.py."""

import json
import re
from pathlib import Path

from pipeline.location.constants import (
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


class TestCountriesConstant:
    """Test suite for COUNTRIES constant."""

    def test_countries_is_frozenset(self):
        assert isinstance(COUNTRIES, frozenset)

    def test_countries_not_empty(self):
        assert len(COUNTRIES) > 0

    def test_countries_contains_expected_countries(self):
        expected = {"United States", "United Kingdom", "Canada", "Germany", "France"}
        for country in expected:
            assert country in COUNTRIES

    def test_countries_count_reasonable(self):
        assert len(COUNTRIES) >= 150

    def test_countries_all_strings(self):
        for country in COUNTRIES:
            assert isinstance(country, str)
            assert len(country) > 0


class TestCountryAliases:
    """Test suite for COUNTRY_ALIASES constant."""

    def test_country_aliases_is_dict(self):
        assert isinstance(COUNTRY_ALIASES, dict)

    def test_country_aliases_not_empty(self):
        assert len(COUNTRY_ALIASES) > 0

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

    def test_country_aliases_keys_are_lowercase(self):
        for alias in COUNTRY_ALIASES.keys():
            assert alias == alias.lower()


class TestUSStateAbbreviations:
    """Test suite for US_STATE_ABBREVIATIONS constant."""

    def test_us_state_abbreviations_is_frozenset(self):
        assert isinstance(US_STATE_ABBREVIATIONS, frozenset)

    def test_us_state_abbreviations_has_50_states_plus_dc(self):
        assert len(US_STATE_ABBREVIATIONS) == 51

    def test_us_state_abbreviations_contains_expected_states(self):
        expected = {"CA", "NY", "TX", "FL", "WA", "DC"}
        for state in expected:
            assert state in US_STATE_ABBREVIATIONS

    def test_us_state_abbreviations_all_uppercase(self):
        for abbr in US_STATE_ABBREVIATIONS:
            assert abbr == abbr.upper()
            assert len(abbr) == 2


class TestUSStateToAbbr:
    """Test suite for US_STATE_TO_ABBR constant."""

    def test_us_state_to_abbr_is_dict(self):
        assert isinstance(US_STATE_TO_ABBR, dict)

    def test_us_state_to_abbr_has_50_states_plus_dc(self):
        assert len(US_STATE_TO_ABBR) == 51

    def test_us_state_to_abbr_mappings_correct(self):
        assert US_STATE_TO_ABBR["California"] == "CA"
        assert US_STATE_TO_ABBR["New York"] == "NY"
        assert US_STATE_TO_ABBR["Texas"] == "TX"
        assert US_STATE_TO_ABBR["District of Columbia"] == "DC"

    def test_us_state_to_abbr_values_are_valid_abbreviations(self):
        for state, abbr in US_STATE_TO_ABBR.items():
            assert abbr in US_STATE_ABBREVIATIONS


class TestAbbrToState:
    """Test suite for ABBR_TO_STATE constant."""

    def test_abbr_to_state_is_dict(self):
        assert isinstance(ABBR_TO_STATE, dict)

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
    """Test suite for Canadian province constants."""

    def test_canadian_provinces_is_frozenset(self):
        assert isinstance(CANADIAN_PROVINCES, frozenset)

    def test_canadian_provinces_count(self):
        assert len(CANADIAN_PROVINCES) == 13

    def test_canadian_provinces_contains_expected(self):
        expected = {"ontario", "quebec", "british columbia", "alberta"}
        for province in expected:
            assert province in CANADIAN_PROVINCES

    def test_canadian_province_abbreviations_is_dict(self):
        assert isinstance(CANADIAN_PROVINCE_ABBREVIATIONS, dict)

    def test_canadian_province_abbreviations_count(self):
        assert len(CANADIAN_PROVINCE_ABBREVIATIONS) == 13

    def test_canadian_province_abbreviations_mappings(self):
        assert CANADIAN_PROVINCE_ABBREVIATIONS["ON"] == "Ontario"
        assert CANADIAN_PROVINCE_ABBREVIATIONS["BC"] == "British Columbia"


class TestOtherRegionConstants:
    """Test suite for other regional constants."""

    def test_indian_states_is_frozenset(self):
        assert isinstance(INDIAN_STATES, frozenset)

    def test_indian_states_not_empty(self):
        assert len(INDIAN_STATES) > 20

    def test_indian_states_contains_expected(self):
        assert "karnataka" in INDIAN_STATES
        assert "maharashtra" in INDIAN_STATES
        assert "delhi" in INDIAN_STATES

    def test_australian_states_is_frozenset(self):
        assert isinstance(AUSTRALIAN_STATES, frozenset)

    def test_australian_states_count(self):
        assert len(AUSTRALIAN_STATES) == 8

    def test_german_states_is_frozenset(self):
        assert isinstance(GERMAN_STATES, frozenset)

    def test_german_states_not_empty(self):
        assert len(GERMAN_STATES) > 10

    def test_uk_regions_is_frozenset(self):
        assert isinstance(UK_REGIONS, frozenset)

    def test_uk_regions_contains_expected(self):
        assert "england" in UK_REGIONS
        assert "scotland" in UK_REGIONS
        assert "wales" in UK_REGIONS


class TestInvalidPatterns:
    """Test suite for invalid pattern constants."""

    def test_invalid_city_patterns_is_list(self):
        assert isinstance(INVALID_CITY_PATTERNS, list)

    def test_invalid_city_patterns_not_empty(self):
        assert len(INVALID_CITY_PATTERNS) > 0

    def test_invalid_city_patterns_are_compiled_regex(self):
        import re

        for pattern in INVALID_CITY_PATTERNS:
            assert isinstance(pattern, re.Pattern)

    def test_invalid_states_is_frozenset(self):
        assert isinstance(INVALID_STATES, frozenset)

    def test_invalid_states_contains_expected(self):
        assert "Remote" in INVALID_STATES
        assert "Hybrid" in INVALID_STATES
        assert "N/A" in INVALID_STATES


class TestStateMappings:
    """Test suite for STATE_MAPPINGS constant."""

    def test_state_mappings_is_dict(self):
        assert isinstance(STATE_MAPPINGS, dict)

    def test_state_mappings_not_empty(self):
        assert len(STATE_MAPPINGS) > 100

    def test_state_mappings_dc_variations(self):
        assert STATE_MAPPINGS["Washington D.C."] == "District of Columbia"
        assert STATE_MAPPINGS["Washington, D.C."] == "District of Columbia"
        assert STATE_MAPPINGS["District Of Columbia"] == "District of Columbia"

    def test_state_mappings_can_return_none(self):
        assert STATE_MAPPINGS.get("Remote") is None


class TestCitiesAsStates:
    """Test suite for CITIES_AS_STATES constant."""

    def test_cities_as_states_is_dict(self):
        assert isinstance(CITIES_AS_STATES, dict)

    def test_cities_as_states_not_empty(self):
        assert len(CITIES_AS_STATES) > 100

    def test_cities_as_states_contains_major_cities(self):
        assert "London" in CITIES_AS_STATES
        assert "Paris" in CITIES_AS_STATES
        assert "Tokyo" in CITIES_AS_STATES
        assert "Sydney" in CITIES_AS_STATES


class TestCountriesAsCities:
    """Test suite for COUNTRIES_AS_CITIES constant."""

    def test_countries_as_cities_is_frozenset(self):
        assert isinstance(COUNTRIES_AS_CITIES, frozenset)

    def test_countries_as_cities_not_empty(self):
        assert len(COUNTRIES_AS_CITIES) > 100

    def test_countries_as_cities_all_lowercase(self):
        for item in COUNTRIES_AS_CITIES:
            assert item == item.lower()


class TestCountriesAsStates:
    """Test suite for COUNTRIES_AS_STATES constant."""

    def test_countries_as_states_is_dict(self):
        assert isinstance(COUNTRIES_AS_STATES, dict)

    def test_countries_as_states_not_empty(self):
        assert len(COUNTRIES_AS_STATES) > 50

    def test_countries_as_states_mappings(self):
        assert COUNTRIES_AS_STATES["Singapore"] == "Singapore"
        assert COUNTRIES_AS_STATES["Hong Kong"] == "Hong Kong"


class TestUSCities:
    """Test suite for US_CITIES constant."""

    def test_us_cities_is_frozenset(self):
        assert isinstance(US_CITIES, frozenset)

    def test_us_cities_raw_json_has_156_entries(self):
        data_path = Path(__file__).parents[2] / "location" / "data" / "location_constants.json"
        with data_path.open(encoding="utf-8") as f:
            data = json.load(f)
        assert len(data["us_cities"]) == 156

    def test_us_cities_unique_156(self):
        assert len(US_CITIES) == 156

    def test_removed_disputed_values_not_in_us(self):
        assert "vancouver" not in US_CITIES
        assert "birmingham" not in US_CITIES


class TestInternationalCities:
    """Test suite for INTERNATIONAL_CITIES constant."""

    def test_international_cities_is_dict(self):
        assert isinstance(INTERNATIONAL_CITIES, dict)

    def test_international_cities_json_has_141_entries(self):
        data_path = Path(__file__).parents[2] / "location" / "data" / "location_constants.json"
        with data_path.open(encoding="utf-8") as f:
            data = json.load(f)
        assert len(data["international_cities"]) == 141

    def test_international_cities_export_has_141(self):
        assert len(INTERNATIONAL_CITIES) == 141

    def test_international_cities_disputed(self):
        assert INTERNATIONAL_CITIES["vancouver"] == "Canada"
        assert INTERNATIONAL_CITIES["birmingham"] == "United Kingdom"


class TestCountryPatternPairs:
    """Test suite for COUNTRY_PATTERN_PAIRS constant."""

    def test_is_list_of_tuples(self):
        assert isinstance(COUNTRY_PATTERN_PAIRS, list)
        for item in COUNTRY_PATTERN_PAIRS:
            assert isinstance(item, tuple)
            assert len(item) == 2
            assert isinstance(item[0], re.Pattern)
            assert isinstance(item[1], str)

    def test_exact_count(self):
        assert len(COUNTRY_PATTERN_PAIRS) == 75

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
    """Test suite for COUNTRY_ABBR_PATTERN_PAIRS constant."""

    def test_is_list_of_tuples(self):
        assert isinstance(COUNTRY_ABBR_PATTERN_PAIRS, list)
        for item in COUNTRY_ABBR_PATTERN_PAIRS:
            assert isinstance(item, tuple)
            assert len(item) == 2
            assert isinstance(item[0], re.Pattern)
            assert isinstance(item[1], str)

    def test_exact_count(self):
        assert len(COUNTRY_ABBR_PATTERN_PAIRS) == 72

    def test_first_and_last_ordering(self):
        assert COUNTRY_ABBR_PATTERN_PAIRS[0][1] == "United States"
        assert COUNTRY_ABBR_PATTERN_PAIRS[-1][1] == "Cyprus"

    def test_patterns_have_IGNORECASE(self):
        for pattern, _ in COUNTRY_ABBR_PATTERN_PAIRS:
            assert pattern.flags & re.IGNORECASE

    def test_usa_pattern_matches(self):
        assert COUNTRY_ABBR_PATTERN_PAIRS[0][1] == "United States"


class TestCountryAbbrevFullMatch:
    """Test suite for COUNTRY_ABBREV_FULL_MATCH constant."""

    def test_is_dict(self):
        assert isinstance(COUNTRY_ABBREV_FULL_MATCH, dict)

    def test_exact_count(self):
        assert len(COUNTRY_ABBREV_FULL_MATCH) == 78

    def test_ua_maps_to_ukraine(self):
        assert COUNTRY_ABBREV_FULL_MATCH["ua"] == "Ukraine"

    def test_boundary_values(self):
        assert COUNTRY_ABBREV_FULL_MATCH["us"] == "United States"
        assert COUNTRY_ABBREV_FULL_MATCH["gb"] == "United Kingdom"
        assert COUNTRY_ABBREV_FULL_MATCH["in"] == "India"
        assert COUNTRY_ABBREV_FULL_MATCH["mt"] == "Malta"

    def test_keys_are_lowercase(self):
        for key in COUNTRY_ABBREV_FULL_MATCH:
            assert key == key.lower()


class TestCountryAliasesMerge:
    """Test suite for COUNTRY_ALIASES after inline merge."""

    def test_is_dict(self):
        assert isinstance(COUNTRY_ALIASES, dict)

    def test_merged_count_is_16(self):
        assert len(COUNTRY_ALIASES) == 16

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
    """Test suite for US_STATES_FULL constant."""

    def test_is_frozenset(self):
        assert isinstance(US_STATES_FULL, frozenset)

    def test_exact_count(self):
        assert len(US_STATES_FULL) == 51

    def test_contains_all_states_and_dc(self):
        assert "california" in US_STATES_FULL
        assert "new york" in US_STATES_FULL
        assert "texas" in US_STATES_FULL
        assert "district of columbia" in US_STATES_FULL

    def test_all_lowercase(self):
        for state in US_STATES_FULL:
            assert state == state.lower()


class TestFrenchRegions:
    """Test suite for FRENCH_REGIONS constant."""

    def test_is_frozenset(self):
        assert isinstance(FRENCH_REGIONS, frozenset)

    def test_exact_count(self):
        assert len(FRENCH_REGIONS) == 13

    def test_contains_expected(self):
        assert "île-de-france" in FRENCH_REGIONS
        assert "corse" in FRENCH_REGIONS
        assert "normandie" in FRENCH_REGIONS


class TestItalianRegions:
    """Test suite for ITALIAN_REGIONS constant."""

    def test_is_frozenset(self):
        assert isinstance(ITALIAN_REGIONS, frozenset)

    def test_exact_count(self):
        assert len(ITALIAN_REGIONS) == 25

    def test_contains_expected(self):
        assert "lazio" in ITALIAN_REGIONS
        assert "lombardy" in ITALIAN_REGIONS
        assert "veneto" in ITALIAN_REGIONS


class TestSpanishRegions:
    """Test suite for SPANISH_REGIONS constant."""

    def test_is_frozenset(self):
        assert isinstance(SPANISH_REGIONS, frozenset)

    def test_exact_count(self):
        assert len(SPANISH_REGIONS) == 27

    def test_contains_expected(self):
        assert "andalusia" in SPANISH_REGIONS
        assert "madrid" in SPANISH_REGIONS
        assert "valencia" in SPANISH_REGIONS


class TestMexicanStates:
    """Test suite for MEXICAN_STATES constant."""

    def test_is_frozenset(self):
        assert isinstance(MEXICAN_STATES, frozenset)

    def test_exact_count(self):
        assert len(MEXICAN_STATES) == 34

    def test_contains_expected(self):
        assert "jalisco" in MEXICAN_STATES
        assert "mexico city" in MEXICAN_STATES
        assert "ciudad de méxico" in MEXICAN_STATES


class TestBrazilianStates:
    """Test suite for BRAZILIAN_STATES constant."""

    def test_is_frozenset(self):
        assert isinstance(BRAZILIAN_STATES, frozenset)

    def test_exact_count(self):
        assert len(BRAZILIAN_STATES) == 27

    def test_contains_expected(self):
        assert "são paulo" in BRAZILIAN_STATES
        assert "rio de janeiro" in BRAZILIAN_STATES
        assert "acre" in BRAZILIAN_STATES


class TestCountryNamesAsStates:
    """Test suite for COUNTRY_NAMES_AS_STATES constant."""

    def test_is_frozenset(self):
        assert isinstance(COUNTRY_NAMES_AS_STATES, frozenset)

    def test_exact_count(self):
        assert len(COUNTRY_NAMES_AS_STATES) == 30

    def test_contains_expected(self):
        assert "United States" in COUNTRY_NAMES_AS_STATES
        assert "Australia" in COUNTRY_NAMES_AS_STATES
        assert "India" in COUNTRY_NAMES_AS_STATES
        assert "Hong Kong" in COUNTRY_NAMES_AS_STATES


class TestSinglePartCountryNames:
    """Test suite for SINGLE_PART_COUNTRY_NAMES constant."""

    def test_is_frozenset(self):
        assert isinstance(SINGLE_PART_COUNTRY_NAMES, frozenset)

    def test_exact_count(self):
        assert len(SINGLE_PART_COUNTRY_NAMES) == 36

    def test_contains_expected(self):
        assert "united states" in SINGLE_PART_COUNTRY_NAMES
        assert "us" in SINGLE_PART_COUNTRY_NAMES
        assert "uk" in SINGLE_PART_COUNTRY_NAMES
        assert "china" in SINGLE_PART_COUNTRY_NAMES

    def test_all_lowercase(self):
        for name in SINGLE_PART_COUNTRY_NAMES:
            assert name == name.lower()


class TestMajorCityStateNames:
    """Test suite for MAJOR_CITY_STATE_NAMES constant."""

    def test_is_frozenset(self):
        assert isinstance(MAJOR_CITY_STATE_NAMES, frozenset)

    def test_exact_count(self):
        assert len(MAJOR_CITY_STATE_NAMES) == 10

    def test_contains_expected(self):
        assert "new york" in MAJOR_CITY_STATE_NAMES
        assert "delhi" in MAJOR_CITY_STATE_NAMES
        assert "washington" in MAJOR_CITY_STATE_NAMES

    def test_all_lowercase(self):
        for name in MAJOR_CITY_STATE_NAMES:
            assert name == name.lower()
