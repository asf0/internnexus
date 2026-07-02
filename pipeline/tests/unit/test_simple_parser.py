"""Unit tests for pipeline/location/simple_parser.py."""

from __future__ import annotations

import pytest

from pipeline.location.simple_parser import (
    extract_city_from_street_address,
    extract_state,
    infer_country_from_state,
    normalize_location,
)


class TestExtractState:
    def test_us_state_abbreviation(self) -> None:
        assert extract_state("Austin, TX") == "Texas"

    def test_canadian_province_abbreviation(self) -> None:
        assert extract_state("Toronto, ON") == "Ontario"

    def test_us_state_full_name(self) -> None:
        assert extract_state("California") == "California"

    def test_german_state_full_name(self) -> None:
        assert extract_state("Bavaria") == "Bavaria"

    def test_special_state_mapping(self) -> None:
        assert extract_state("NSW") == "New South Wales"

    def test_strips_zip_code(self) -> None:
        assert extract_state("Austin, TX 78701") == "Texas"

    def test_rejects_country_names(self) -> None:
        assert extract_state("Germany") is None

    def test_returns_none_for_empty(self) -> None:
        assert extract_state("") is None


class TestInferCountryFromState:
    def test_us_state(self) -> None:
        assert infer_country_from_state("California") == "United States"

    def test_canadian_province(self) -> None:
        assert infer_country_from_state("Ontario") == "Canada"

    def test_german_state(self) -> None:
        assert infer_country_from_state("Bavaria") == "Germany"

    def test_none_returns_none(self) -> None:
        assert infer_country_from_state(None) is None


class TestNormalizeLocation:
    def test_empty_location(self) -> None:
        result = normalize_location("")
        assert result["city"] is None
        assert result["state"] is None
        assert result["country"] is None
        assert result["is_remote"] is False

    def test_remote(self) -> None:
        result = normalize_location("Remote")
        assert result["is_remote"] is True
        assert result["city"] is None

    def test_remote_with_country(self) -> None:
        result = normalize_location("Remote - US")
        assert result["is_remote"] is True
        assert result["country"] == "United States"

    def test_single_city_with_state_abbreviation(self) -> None:
        result = normalize_location("Austin, TX")
        assert result["city"] == "Austin"
        assert result["state"] == "Texas"
        assert result["country"] == "United States"

    def test_two_parts_city_country(self) -> None:
        result = normalize_location("London, UK")
        assert result["city"] == "London"
        assert result["country"] == "United Kingdom"

    def test_single_country_name(self) -> None:
        result = normalize_location("Canada")
        assert result["city"] is None
        assert result["country"] == "Canada"

    def test_three_parts_city_state_country(self) -> None:
        result = normalize_location("San Francisco, CA, US")
        assert result["city"] == "San Francisco"
        assert result["state"] == "California"
        assert result["country"] == "United States"

    def test_city_only_major_city(self) -> None:
        result = normalize_location("Paris")
        assert result["city"] == "Paris"
        assert result["country"] == "France"

    def test_multi_location_takes_first(self) -> None:
        result = normalize_location("Austin, TX; Denver, CO")
        assert result["city"] == "Austin"
        assert result["state"] == "Texas"

    def test_trailing_remote_indicator(self) -> None:
        result = normalize_location("Austin, TX (Remote)")
        # The trailing "(Remote)" is not in the remote keyword list, so it
        # becomes part of the last comma-split segment and is treated as a fake
        # city indicator, leaving Austin/TX.
        assert result["city"] == "Austin"
        assert result["state"] == "Texas"

    def test_two_different_us_states_returns_country_only(self) -> None:
        result = normalize_location("California, Washington")
        assert result["city"] is None
        assert result["country"] == "United States"

    def test_state_only(self) -> None:
        result = normalize_location("Texas")
        assert result["state"] == "Texas"
        assert result["country"] == "United States"

    def test_repeated_city_as_state(self) -> None:
        result = normalize_location("Tokyo, Tokyo, Japan")
        assert result["city"] == "Tokyo"
        assert result["country"] == "Japan"

    # PR5 regression tests — Vancouver/Birmingham city collisions
    def test_vancouver_alone_infers_canada(self) -> None:
        result = normalize_location("Vancouver")
        assert result["country"] == "Canada"

    def test_vancouver_wa_infers_united_states(self) -> None:
        result = normalize_location("Vancouver, WA")
        assert result["country"] == "United States"

    def test_birmingham_alone_infers_united_kingdom(self) -> None:
        result = normalize_location("Birmingham")
        assert result["country"] == "United Kingdom"

    def test_birmingham_al_infers_united_states(self) -> None:
        result = normalize_location("Birmingham, AL")
        assert result["country"] == "United States"


class TestStreetTypeBldg:
    """PR5 regression — bldv→bldg typo fix."""

    def test_street_type_bldg_recognized(self) -> None:
        assert extract_city_from_street_address("123 Main Bldg Springfield") == "Springfield"
