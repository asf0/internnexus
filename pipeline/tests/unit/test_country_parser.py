"""Direct unit tests for country extraction and normalization helpers."""

from __future__ import annotations

import pytest

from pipeline.location.country_parser import (
    _normalize_country_name,
    _strip_region_codes,
    extract_country_from_text,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Canada", "Canada"),
        ("DE", "Germany"),
        ("Berlin, DE", "Germany"),
        ("Turkiye", "Turkey"),
        ("Czech Republic", "Czechia"),
        ("UAE", "United Arab Emirates"),
        ("Germany, EMEA", "Germany"),
        ("Atlantis", None),
        ("beginning", None),
        ("cAnAdA", "Canada"),
    ],
)
def test_extract_country_from_text(text: str, expected: str | None) -> None:
    assert extract_country_from_text(text) == expected


@pytest.mark.parametrize(
    ("country", "expected"),
    [
        ("US", "United States"),
        ("GB", "United Kingdom"),
        ("USA", "United States"),
        ("UK", "United Kingdom"),
        ("Turkiye", "Turkey"),
        ("Czech Republic", "Czechia"),
        ("Unknown", "Unknown"),
        ("Canada", "Canada"),
    ],
)
def test_normalize_country_name(country: str, expected: str) -> None:
    assert _normalize_country_name(country) == expected


@pytest.mark.parametrize("region_code", ["EMEA", "APAC", "AMER", "LATAM"])
def test_strip_region_codes(region_code: str) -> None:
    assert _strip_region_codes(f"Germany, {region_code}") == "Germany"


def test_strip_region_codes_leaves_text_without_suffix() -> None:
    assert _strip_region_codes("Germany") == "Germany"


def test_strip_region_codes_removes_only_final_suffix() -> None:
    assert _strip_region_codes("Germany, EMEA, APAC") == "Germany, EMEA"


def test_strip_region_codes_accepts_empty_text() -> None:
    assert _strip_region_codes("") == ""
