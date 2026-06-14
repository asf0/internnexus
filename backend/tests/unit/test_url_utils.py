"""Tests for backend URL utilities."""

from __future__ import annotations

import pytest

from app.utils.url import add_utm_params, is_valid_url


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://example.com/apply", True),
        ("http://example.com/apply", True),
        ("ftp://example.com/apply", False),
        ("https://", False),
        ("example.com/apply", False),
        ("", False),
        ("javascript:alert(1)", False),
        ("data:text/html,hi", False),
        ("blob:https://example.com/id", False),
    ],
)
def test_is_valid_url(url: str, expected: bool) -> None:
    assert is_valid_url(url) is expected


def test_is_valid_url_rejects_non_string_input() -> None:
    # urlparse raises TypeError for non-string input; we should still return False safely.
    assert is_valid_url(None) is False  # type: ignore[arg-type]
    assert is_valid_url(12345) is False  # type: ignore[arg-type]


def test_add_utm_params_appends_source_and_preserves_existing() -> None:
    result = add_utm_params("https://example.com/apply?ref=123", medium="web")
    assert "utm_source=internnexus" in result
    assert "utm_medium=web" in result
    assert "ref=123" in result
