"""Tests for backend URL utilities."""

from __future__ import annotations

from app.infra.url import add_utm_params


def test_add_utm_params_appends_source_and_preserves_existing() -> None:
    result = add_utm_params("https://example.com/apply?ref=123", medium="web")
    assert "utm_source=internnexus" in result
    assert "utm_medium=web" in result
    assert "ref=123" in result
