"""Direct unit tests for state, province, and region parsing helpers."""

from __future__ import annotations

import pytest

from pipeline.location.state_parser import (
    _lookup_special_state_mapping,
    _lookup_state_abbreviation,
    _match_full_state_name,
    expand_state_abbreviation,
    normalize_state_name,
)


@pytest.mark.parametrize(
    ("abbreviation", "country_hint", "expected"),
    [
        ("CA", None, "California"),
        ("ON", None, "Ontario"),
        ("KA", "India", "Karnataka"),
        ("ZZ", None, None),
        ("", None, None),
        ("ca", None, "California"),
    ],
)
def test_expand_state_abbreviation(
    abbreviation: str,
    country_hint: str | None,
    expected: str | None,
) -> None:
    assert expand_state_abbreviation(abbreviation, country_hint) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("NSW", "New South Wales"),
        ("Germany", None),
        ("Atlantis", None),
        ("", None),
    ],
)
def test_lookup_special_state_mapping(text: str, expected: str | None) -> None:
    assert _lookup_special_state_mapping(text) == expected


@pytest.mark.parametrize(
    ("text", "country_hint", "expected"),
    [
        ("Austin, TX", None, "Texas"),
        ("Austin", None, None),
        ("CA NY", None, "California"),
    ],
)
def test_lookup_state_abbreviation(
    text: str,
    country_hint: str | None,
    expected: str | None,
) -> None:
    assert _lookup_state_abbreviation(text, country_hint) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("California", "California"),
        ("Ontario", "Ontario"),
        ("Karnataka", "Karnataka"),
        ("New South Wales", "New South Wales"),
        ("Bavaria", "Bavaria"),
        ("England", "England"),
        ("Atlantis", None),
    ],
)
def test_match_full_state_name(text: str, expected: str | None) -> None:
    assert _match_full_state_name(text) == expected


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("Bayern", "Bavaria"),
        ("Atlantis", "Atlantis"),
        ("", ""),
        ("bayern", "bayern"),
        ("São Paulo", "São Paulo"),
        ("Bayern ", "Bavaria"),
        ("Washington D.C.", "District of Columbia"),
        ("Remote", None),
    ],
)
def test_normalize_state_name(state: str, expected: str | None) -> None:
    assert normalize_state_name(state) == expected
