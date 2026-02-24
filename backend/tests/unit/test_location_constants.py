"""Unit tests for pipeline/location/constants.py."""

import pytest

from pipeline.location.constants import (
    ABBR_TO_STATE,
    CANADIAN_PROVINCES,
    CANADIAN_PROVINCE_ABBREVIATIONS,
    CITIES_AS_STATES,
    COUNTRIES,
    COUNTRIES_AS_CITIES,
    COUNTRIES_AS_STATES,
    COUNTRY_ALIASES,
    GERMAN_STATES,
    INDIAN_STATES,
    INVALID_CITY_PATTERNS,
    INVALID_STATES,
    STATE_MAPPINGS,
    STATES_AS_CITIES,
    UK_REGIONS,
    US_STATE_ABBREVIATIONS,
    US_STATE_TO_ABBR,
    AUSTRALIAN_STATES,
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
