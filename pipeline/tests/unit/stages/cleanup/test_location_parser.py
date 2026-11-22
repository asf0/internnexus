"""Unit tests for pipeline/stages/cleanup/location_parser.py."""

from unittest.mock import MagicMock, patch

import pytest

from pipeline.stages.cleanup.location_parser import (
    _is_plain_remote,
    _parse_location_only,
)

_CACHE_TARGET = "pipeline.stages.cleanup.location_parser.get_location_cache"

#: Sentinel for a field the original test did not assert on.
ANY = object()


@pytest.fixture
def mock_cache():
    cache = MagicMock()
    cache.get = MagicMock(return_value=None)
    cache.set = MagicMock(return_value=None)
    return cache


# ---------------------------------------------------------------------------
# _is_plain_remote
# ---------------------------------------------------------------------------

PLAIN_REMOTE = [
    "Remote", "remote", "REMOTE",
    "Work from home", "work from home", "WFH", "wfh",
    "Distributed", "distributed",
    "Virtual", "virtual",
    "Telecommute", "telecommute",
    "Anywhere", "anywhere",
    "  remote  ", "\tremote\t",
]

NOT_PLAIN_REMOTE = [
    "San Francisco", "New York", "London",
    "Remote - US", "Remote, USA",
]


@pytest.mark.parametrize("value", PLAIN_REMOTE)
def test_is_plain_remote_accepts(value):
    assert _is_plain_remote(value) is True


@pytest.mark.parametrize("value", NOT_PLAIN_REMOTE)
def test_is_plain_remote_rejects(value):
    assert _is_plain_remote(value) is False


# ---------------------------------------------------------------------------
# _parse_location_only
# ---------------------------------------------------------------------------

# (raw location, expected city, expected state, expected country)
# ANY marks a field the original per-case test did not assert.
PARSE_CASES = [
    ("Remote", None, None, None),
    ("San Francisco, CA", "San Francisco", "California", "United States"),
    ("New York, NY", "New York", "New York", "United States"),
    ("London, UK", "London", ANY, "United Kingdom"),
    ("San Francisco", "San Francisco", ANY, "United States"),
    ("Mountain View", "Mountain View", ANY, "United States"),
    ("Amsterdam", "Amsterdam", ANY, "Netherlands"),
    ("London", "London", ANY, "United Kingdom"),
    ("Toronto", "Toronto", ANY, "Canada"),
    ("Bengaluru", "Bengaluru", ANY, "India"),
    ("Sydney", "Sydney", ANY, "Australia"),
    ("Berlin", "Berlin", ANY, "Germany"),
    ("Tokyo", "Tokyo", ANY, "Japan"),
    ("Singapore", "Singapore", ANY, "Singapore"),
    ("Paris", "Paris", ANY, "France"),
    ("Dublin", "Dublin", ANY, "Ireland"),
    ("Belgrade", "Belgrade", ANY, "Serbia"),
    ("Barcelona", "Barcelona", ANY, "Spain"),
    ("Seoul", "Seoul", ANY, "South Korea"),
    ("Tel Aviv", "Tel Aviv", ANY, "Israel"),
    ("Dubai", "Dubai", ANY, "United Arab Emirates"),
    ("Mexico City", "Mexico City", ANY, "Mexico"),
    ("Sao Paulo", "Sao Paulo", ANY, "Brazil"),
    ("Vancouver", "Vancouver", ANY, "Canada"),
    ("Montreal", "Montreal", ANY, "Canada"),
    ("NYC", "New York", ANY, "United States"),
    ("SF", "San Francisco", ANY, "United States"),
]


@pytest.mark.parametrize(
    ("raw", "city", "state", "country"),
    PARSE_CASES,
    ids=[case[0] for case in PARSE_CASES],
)
def test_parse_location_only(raw, city, state, country, mock_cache):
    with patch(_CACHE_TARGET, return_value=mock_cache):
        result = _parse_location_only(raw)

    assert result["city"] == city
    assert result["country"] == country
    if state is not ANY:
        assert result["state"] == state


def test_parse_returns_cached_result_without_rewriting(mock_cache):
    from pipeline.stages.cleanup.location.cache import ParsedLocation

    mock_cache.get = MagicMock(
        return_value=ParsedLocation(city="Cached City", state="Cached State", country="Cached Country")
    )

    with patch(_CACHE_TARGET, return_value=mock_cache):
        result = _parse_location_only("Any Location")

    assert result["city"] == "Cached City"
    assert result["state"] == "Cached State"
    assert result["country"] == "Cached Country"
    mock_cache.set.assert_not_called()


def test_parse_caches_result(mock_cache):
    with patch(_CACHE_TARGET, return_value=mock_cache):
        _parse_location_only("Seattle, WA")

    mock_cache.set.assert_called_once()
