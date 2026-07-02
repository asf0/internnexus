"""Direct unit tests for location normalization orchestration helpers."""

from __future__ import annotations

from typing import Any

import pytest

from pipeline.location.normalize import (
    _build_empty_result,
    _detect_remote,
    _infer_and_validate_country,
    _parse_one_part,
    _parse_three_or_more,
    _parse_two_parts,
    _split_and_clean_parts,
    has_multiple_remote_locations,
    is_remote_pattern,
)


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ("Remote; London", False),
        ("Remote; Remote", True),
        ("Remote | Remote | Remote", True),
        ("London; Paris", False),
    ],
)
def test_has_multiple_remote_locations(location: str, expected: bool) -> None:
    assert has_multiple_remote_locations(location) is expected


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ("Remote", True),
        ("Remote - US", True),
        ("US, Remote", True),
        ("Remote Hybrid", True),
        ("New York", False),
    ],
)
def test_is_remote_pattern(location: str, expected: bool) -> None:
    assert is_remote_pattern(location) is expected


@pytest.mark.parametrize(
    ("location_clean", "location_lower", "expected"),
    [
        ("Remote", "remote", {"is_remote": True}),
        ("Remote - US", "remote - us", {"country": "United States", "is_remote": True}),
        ("London", "london", None),
        ("", "", None),
    ],
)
def test_detect_remote(
    location_clean: str,
    location_lower: str,
    expected: dict[str, Any] | None,
) -> None:
    assert _detect_remote(location_clean, location_lower) == expected


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ("London", (["London"], False)),
        ("Austin, TX", (["Austin", "TX"], False)),
        ("Toronto, ON, Canada", (["Toronto", "ON", "Canada"], False)),
        ("London; Paris", (["London"], False)),
        ("Austin, TX, Remote", (["Austin", "TX"], True)),
    ],
)
def test_split_and_clean_parts(location: str, expected: tuple[list[str], bool]) -> None:
    assert _split_and_clean_parts(location) == expected


@pytest.mark.parametrize(
    ("first_part", "country", "expected"),
    [
        ("123 Main St Springfield", None, ("Springfield", None, None)),
        ("Remote", None, (None, None, None)),
        ("Canada", None, (None, None, "Canada")),
        ("Austin TX", None, ("Austin", "Texas", None)),
        ("London", None, ("London", None, "United Kingdom")),
        ("California", None, (None, "California", None)),
        ("", None, (None, None, None)),
    ],
)
def test_parse_one_part(
    first_part: str,
    country: str | None,
    expected: tuple[str | None, str | None, str | None],
) -> None:
    assert _parse_one_part(first_part, country) == expected


@pytest.mark.parametrize(
    ("first", "second", "country", "expected"),
    [
        ("California", "Washington", None, (None, None, "United States")),
        ("123 Main St Springfield", "IL", None, ("Springfield", "Illinois", None)),
        ("Austin", "TX", None, ("Austin", "Texas", None)),
        ("London", "UK", None, ("London", None, "United Kingdom")),
        ("Remote", "Hybrid", None, (None, None, None)),
    ],
)
def test_parse_two_parts(
    first: str,
    second: str,
    country: str | None,
    expected: tuple[str | None, str | None, str | None],
) -> None:
    assert _parse_two_parts(first, second, country) == expected


@pytest.mark.parametrize(
    ("parts", "country", "expected"),
    [
        (["Toronto", "ON", "Canada"], None, ("Toronto", "Ontario", "Canada")),
        (
            ["123 Main St", "Springfield", "IL", "United States"],
            None,
            ("Springfield", "Illinois", "United States"),
        ),
        (["Atlantis", "Nowhere", "Unknown"], None, ("Atlantis", None, None)),
        (["London; Paris", "Berlin", "Germany"], None, ("London; Paris", "Berlin", "Germany")),
    ],
)
def test_parse_three_or_more(
    parts: list[str],
    country: str | None,
    expected: tuple[str | None, str | None, str | None],
) -> None:
    assert _parse_three_or_more(parts, country) == expected


@pytest.mark.parametrize(
    ("city", "state", "country", "expected"),
    [
        (None, "California", None, ("United States", None)),
        ("London", None, None, ("United Kingdom", "London")),
        ("Canada", None, "Canada", ("Canada", None)),
        ("Texas", None, None, (None, None)),
    ],
)
def test_infer_and_validate_country(
    city: str | None,
    state: str | None,
    country: str | None,
    expected: tuple[str | None, str | None],
) -> None:
    assert _infer_and_validate_country(city, state, country) == expected


def test_build_empty_result_preserves_input() -> None:
    assert _build_empty_result("Unknown") == {
        "full": "Unknown",
        "city": None,
        "state": None,
        "country": None,
        "all_cities": None,
        "is_remote": False,
        "is_multi_location": False,
    }
