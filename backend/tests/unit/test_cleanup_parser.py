"""Unit tests for pipeline/cleanup/parser.py."""

from pathlib import Path

import pytest
from unittest.mock import AsyncMock, patch

from pipeline.cleanup.parser import (
    _is_plain_remote,
    _normalize_for_comparison,
    _contains_normalized,
    _is_metadata_consistent,
    _parse_location_only,
)


class TestIsPlainRemote:
    """Test suite for _is_plain_remote function."""

    def test_remote_returns_true(self):
        assert _is_plain_remote("Remote") is True
        assert _is_plain_remote("remote") is True
        assert _is_plain_remote("REMOTE") is True

    def test_work_from_home_returns_true(self):
        assert _is_plain_remote("Work from home") is True
        assert _is_plain_remote("work from home") is True
        assert _is_plain_remote("WFH") is True
        assert _is_plain_remote("wfh") is True

    def test_distributed_returns_true(self):
        assert _is_plain_remote("Distributed") is True
        assert _is_plain_remote("distributed") is True

    def test_virtual_returns_true(self):
        assert _is_plain_remote("Virtual") is True
        assert _is_plain_remote("virtual") is True

    def test_telecommute_returns_true(self):
        assert _is_plain_remote("Telecommute") is True
        assert _is_plain_remote("telecommute") is True

    def test_anywhere_returns_true(self):
        assert _is_plain_remote("Anywhere") is True
        assert _is_plain_remote("anywhere") is True

    def test_city_name_returns_false(self):
        assert _is_plain_remote("San Francisco") is False
        assert _is_plain_remote("New York") is False
        assert _is_plain_remote("London") is False

    def test_remote_with_suffix_returns_false(self):
        assert _is_plain_remote("Remote - US") is False
        assert _is_plain_remote("Remote, USA") is False

    def test_whitespace_handling(self):
        assert _is_plain_remote("  remote  ") is True
        assert _is_plain_remote("\tremote\t") is True


class TestNormalizeForComparison:
    """Test suite for _normalize_for_comparison function."""

    def test_normalizes_to_lowercase(self):
        assert _normalize_for_comparison("SAN FRANCISCO") == "san francisco"
        assert _normalize_for_comparison("New York") == "new york"

    def test_removes_punctuation(self):
        assert _normalize_for_comparison("St. Louis") == "st louis"
        assert _normalize_for_comparison("São Paulo") == "so paulo"
        assert _normalize_for_comparison("Köln, Germany") == "kln germany"

    def test_collapses_whitespace(self):
        assert _normalize_for_comparison("New   York") == "new york"
        assert _normalize_for_comparison("San  Francisco,  CA") == "san francisco ca"

    def test_handles_none(self):
        assert _normalize_for_comparison(None) == ""

    def test_handles_empty_string(self):
        assert _normalize_for_comparison("") == ""

    def test_handles_whitespace_only(self):
        assert _normalize_for_comparison("   ") == ""


class TestContainsNormalized:
    """Test suite for _contains_normalized function."""

    def test_exact_match(self):
        assert _contains_normalized("San Francisco", "San Francisco") is True

    def test_case_insensitive(self):
        assert _contains_normalized("SAN FRANCISCO", "san francisco") is True
        assert _contains_normalized("san francisco", "SAN FRANCISCO") is True

    def test_substring_match(self):
        assert _contains_normalized("San Francisco, CA", "San Francisco") is True
        assert _contains_normalized("New York City, NY, USA", "New York") is True

    def test_no_match(self):
        assert _contains_normalized("San Francisco", "New York") is False

    def test_punctuation_ignored(self):
        assert _contains_normalized("St. Louis, MO", "St Louis") is True

    def test_handles_none_needle(self):
        assert _contains_normalized("San Francisco", None) is False

    def test_handles_none_haystack(self):
        assert _contains_normalized(None, "San Francisco") is False


class TestIsMetadataConsistent:
    """Test suite for _is_metadata_consistent function."""

    def test_consistent_city_and_country(self):
        location_str = "San Francisco, CA, USA"
        parsed_from_location = {"city": "San Francisco", "country": "United States"}
        metadata_result = {"city": "San Francisco", "country": "United States"}

        assert _is_metadata_consistent(location_str, parsed_from_location, metadata_result) is True

    def test_inconsistent_city(self):
        location_str = "San Francisco, CA"
        parsed_from_location = {"city": "San Francisco"}
        metadata_result = {"city": "Los Angeles"}

        assert _is_metadata_consistent(location_str, parsed_from_location, metadata_result) is False

    def test_country_variations_us(self):
        location_str = "San Francisco, US"
        parsed_from_location = {"country": "US"}
        metadata_result = {"country": "United States"}

        assert _is_metadata_consistent(location_str, parsed_from_location, metadata_result) is True

    def test_country_variations_uk(self):
        location_str = "London, UK"
        parsed_from_location = {"country": "UK"}
        metadata_result = {"country": "United Kingdom"}

        assert _is_metadata_consistent(location_str, parsed_from_location, metadata_result) is True

    def test_remote_with_country_is_inconsistent(self):
        location_str = "Remote"
        parsed_from_location = {}
        metadata_result = {"country": "United States"}

        assert _is_metadata_consistent(location_str, parsed_from_location, metadata_result) is False

    def test_empty_metadata_is_consistent(self):
        location_str = "San Francisco, CA"
        parsed_from_location = {"city": "San Francisco"}
        metadata_result = {}

        assert _is_metadata_consistent(location_str, parsed_from_location, metadata_result) is True

    def test_inconsistent_country(self):
        location_str = "Paris, France"
        parsed_from_location = {"country": "France"}
        metadata_result = {"country": "Germany"}

        assert _is_metadata_consistent(location_str, parsed_from_location, metadata_result) is False


class TestParseLocationOnly:
    """Test suite for _parse_location_only function."""

    @pytest.fixture
    def mock_cache(self):
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock(return_value=None)
        return cache

    @pytest.mark.asyncio
    async def test_parse_remote_location(self, mock_cache):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("Remote")

        assert result["city"] is None
        assert result["state"] is None
        assert result["country"] is None

    @pytest.mark.asyncio
    async def test_parse_san_francisco_ca(self, mock_cache):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("San Francisco, CA")

        assert result["city"] == "San Francisco"
        assert result["state"] == "California"
        assert result["country"] == "United States"

    @pytest.mark.asyncio
    async def test_parse_new_york_ny(self, mock_cache):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("New York, NY")

        assert result["city"] == "New York"
        assert result["state"] == "New York"
        assert result["country"] == "United States"

    @pytest.mark.asyncio
    async def test_parse_london_uk(self, mock_cache):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("London, UK")

        assert result["city"] == "London"
        assert result["country"] == "United Kingdom"

    @pytest.mark.asyncio
    async def test_parse_returns_cached_result(self, mock_cache):
        from pipeline.location.cache import ParsedLocation

        cached = ParsedLocation(
            city="Cached City",
            state="Cached State",
            country="Cached Country",
        )
        mock_cache.get = AsyncMock(return_value=cached)

        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("Any Location")

        assert result["city"] == "Cached City"
        assert result["state"] == "Cached State"
        assert result["country"] == "Cached Country"
        mock_cache.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_parse_caches_result(self, mock_cache):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            await _parse_location_only("Seattle, WA")

        mock_cache.set.assert_called_once()


class TestParseLocationOnlyWithSampleData:
    """Test suite using locations_sample.txt data."""

    @pytest.fixture
    def mock_cache(self):
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock(return_value=None)
        return cache

    @pytest.fixture
    def sample_locations(self):
        locations = []
        fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "locations_sample.txt"
        with fixture_path.open("r") as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split(None, 1)
                    if len(parts) == 2:
                        locations.append(parts[1])
        return locations

    @pytest.mark.asyncio
    async def test_parse_remote_from_sample(self, mock_cache, sample_locations):
        remote_location = "Remote"

        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only(remote_location)

        assert result["city"] is None
        assert result["country"] is None

    @pytest.mark.asyncio
    async def test_parse_san_francisco_from_sample(self, mock_cache, sample_locations):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("San Francisco")

        assert result["city"] == "San Francisco"
        assert result["country"] == "United States"

    @pytest.mark.asyncio
    async def test_parse_mountain_view_from_sample(self, mock_cache, sample_locations):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("Mountain View")

        assert result["city"] == "Mountain View"
        assert result["country"] == "United States"

    @pytest.mark.asyncio
    async def test_parse_amsterdam_from_sample(self, mock_cache, sample_locations):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("Amsterdam")

        assert result["city"] == "Amsterdam"
        assert result["country"] == "Netherlands"

    @pytest.mark.asyncio
    async def test_parse_london_from_sample(self, mock_cache, sample_locations):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("London")

        assert result["city"] == "London"
        assert result["country"] == "United Kingdom"

    @pytest.mark.asyncio
    async def test_parse_toronto_from_sample(self, mock_cache, sample_locations):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("Toronto")

        assert result["city"] == "Toronto"
        assert result["country"] == "Canada"

    @pytest.mark.asyncio
    async def test_parse_bengaluru_from_sample(self, mock_cache, sample_locations):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("Bengaluru")

        assert result["city"] == "Bengaluru"
        assert result["country"] == "India"

    @pytest.mark.asyncio
    async def test_parse_sydney_from_sample(self, mock_cache, sample_locations):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("Sydney")

        assert result["city"] == "Sydney"
        assert result["country"] == "Australia"

    @pytest.mark.asyncio
    async def test_parse_berlin_from_sample(self, mock_cache, sample_locations):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("Berlin")

        assert result["city"] == "Berlin"
        assert result["country"] == "Germany"

    @pytest.mark.asyncio
    async def test_parse_tokyo_from_sample(self, mock_cache, sample_locations):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("Tokyo")

        assert result["city"] == "Tokyo"
        assert result["country"] == "Japan"

    @pytest.mark.asyncio
    async def test_parse_singapore_from_sample(self, mock_cache, sample_locations):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("Singapore")

        assert result["city"] == "Singapore"
        assert result["country"] == "Singapore"

    @pytest.mark.asyncio
    async def test_parse_paris_from_sample(self, mock_cache, sample_locations):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("Paris")

        assert result["city"] == "Paris"
        assert result["country"] == "France"

    @pytest.mark.asyncio
    async def test_parse_dublin_from_sample(self, mock_cache, sample_locations):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("Dublin")

        assert result["city"] == "Dublin"
        assert result["country"] == "Ireland"

    @pytest.mark.asyncio
    async def test_parse_belgrade_from_sample(self, mock_cache, sample_locations):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("Belgrade")

        assert result["city"] == "Belgrade"
        assert result["country"] == "Serbia"

    @pytest.mark.asyncio
    async def test_parse_barcelona_from_sample(self, mock_cache, sample_locations):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("Barcelona")

        assert result["city"] == "Barcelona"
        assert result["country"] == "Spain"

    @pytest.mark.asyncio
    async def test_parse_seoul_from_sample(self, mock_cache, sample_locations):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("Seoul")

        assert result["city"] == "Seoul"
        assert result["country"] == "South Korea"

    @pytest.mark.asyncio
    async def test_parse_tel_aviv_from_sample(self, mock_cache, sample_locations):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("Tel Aviv")

        assert result["city"] == "Tel Aviv"
        assert result["country"] == "Israel"

    @pytest.mark.asyncio
    async def test_parse_dubai_from_sample(self, mock_cache, sample_locations):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("Dubai")

        assert result["city"] == "Dubai"
        assert result["country"] == "United Arab Emirates"

    @pytest.mark.asyncio
    async def test_parse_mexico_city_from_sample(self, mock_cache, sample_locations):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("Mexico City")

        assert result["city"] == "Mexico City"
        assert result["country"] == "Mexico"

    @pytest.mark.asyncio
    async def test_parse_sao_paulo_from_sample(self, mock_cache, sample_locations):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("Sao Paulo")

        assert result["city"] == "Sao Paulo"
        assert result["country"] == "Brazil"

    @pytest.mark.asyncio
    async def test_parse_vancouver_from_sample(self, mock_cache, sample_locations):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("Vancouver")

        assert result["city"] == "Vancouver"
        assert result["country"] == "Canada"

    @pytest.mark.asyncio
    async def test_parse_montreal_from_sample(self, mock_cache, sample_locations):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("Montreal")

        assert result["city"] == "Montreal"
        assert result["country"] == "Canada"

    @pytest.mark.asyncio
    async def test_parse_nyc_abbreviation(self, mock_cache, sample_locations):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("NYC")

        assert result["city"] == "New York"
        assert result["country"] == "United States"

    @pytest.mark.asyncio
    async def test_parse_sf_abbreviation(self, mock_cache, sample_locations):
        with patch("pipeline.cleanup.parser.get_location_cache", return_value=mock_cache):
            result = await _parse_location_only("SF")

        assert result["city"] == "San Francisco"
        assert result["country"] == "United States"
