"""Direct unit tests for city recognition, cleanup, and country inference."""

from __future__ import annotations

import pytest

from pipeline.location.city_parser import (
    _strip_zip_code,
    clean_city_name,
    extract_city_before_state,
    extract_city_from_street_address,
    infer_country_from_city,
    is_fake_city,
    is_street_address,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("123 Main St", True),
        ("1 Main Drive", True),
        ("1 Main Dr", True),
        ("Main St", False),
        ("", False),
    ],
)
def test_is_street_address(text: str, expected: bool) -> None:
    assert is_street_address(text) is expected


@pytest.mark.parametrize(
    ("city", "expected"),
    [
        ("Remote", True),
        ("Hybrid", True),
        ("Multiple Locations", True),
        ("Various", True),
        ("TBD", True),
        ("Real City", False),
        ("Office", True),
        ("Remote - US", True),
    ],
)
def test_is_fake_city(city: str, expected: bool) -> None:
    assert is_fake_city(city) is expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("123 Main St, Austin", ", Austin"),
        ("123 Main St Suite 100, Austin", None),
        ("123 Main St, Remote", None),
        ("Austin, TX", "Austin, TX"),
        ("", None),
    ],
)
def test_extract_city_from_street_address(text: str, expected: str | None) -> None:
    assert extract_city_from_street_address(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Austin TX", "Austin"),
        ("Austin, TX", "Austin,"),
        ("Remote, TX", None),
        ("New York NY", "New York"),
    ],
)
def test_extract_city_before_state(text: str, expected: str | None) -> None:
    assert extract_city_before_state(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Austin 78701", "Austin"),
        ("Austin, TX 78701-1234", "Austin, TX"),
        ("Austin 78701 12345", "Austin 78701"),
    ],
)
def test_strip_zip_code(text: str, expected: str) -> None:
    assert _strip_zip_code(text) == expected


@pytest.mark.parametrize(
    ("city", "expected"),
    [
        ("London", "London"),
        ("United States", None),
        ("California", None),
        ("New York", "New York"),
        ("Austin or Denver", None),
        ("Australia - Sydney", "Sydney"),
        ("Austin, TX", "Austin"),
        ("Austin 78701", "Austin"),
        ("Paris City", "Paris"),
        ("", None),
        ("Hybrid", None),
        ("london", "london"),
    ],
)
def test_clean_city_name(city: str, expected: str | None) -> None:
    assert clean_city_name(city) == expected


@pytest.mark.parametrize(
    ("city", "expected"),
    [
        ("New York", "United States"),
        ("London", "United Kingdom"),
        ("Singapore", "Singapore"),
        ("Vancouver", "Canada"),
        ("Birmingham", "United Kingdom"),
        ("Atlantis", None),
        ("Remote", None),
        ("", None),
    ],
)
def test_infer_country_from_city(city: str, expected: str | None) -> None:
    assert infer_country_from_city(city) == expected
