"""Tests for CSV export formula injection prevention."""

from __future__ import annotations

import pytest

from app.api.admin.users import _sanitize_csv_cell


class TestSanitizeCsvCell:
    """Tests for _sanitize_csv_cell helper."""

    def test_normal_value_unchanged(self) -> None:
        assert _sanitize_csv_cell("John Doe") == "John Doe"

    def test_email_unchanged(self) -> None:
        assert _sanitize_csv_cell("user@example.com") == "user@example.com"

    def test_none_returns_empty(self) -> None:
        assert _sanitize_csv_cell(None) == ""

    def test_empty_string_unchanged(self) -> None:
        assert _sanitize_csv_cell("") == ""

    def test_formula_equals_neutralized(self) -> None:
        assert _sanitize_csv_cell("=cmd|' /C calc'!A0") == "'=cmd|' /C calc'!A0"

    def test_formula_plus_neutralized(self) -> None:
        assert _sanitize_csv_cell("+SUM(A1:A10)") == "'+SUM(A1:A10)"

    def test_formula_minus_neutralized(self) -> None:
        assert _sanitize_csv_cell("-2+3") == "'-2+3"

    def test_formula_at_neutralized(self) -> None:
        assert _sanitize_csv_cell("@SUM(A1)") == "'@SUM(A1)"

    def test_formula_tab_neutralized(self) -> None:
        assert _sanitize_csv_cell("\t=cmd") == "'\t=cmd"

    def test_formula_cr_neutralized(self) -> None:
        assert _sanitize_csv_cell("\r=cmd") == "'\r=cmd"

    def test_leading_whitespace_then_formula_neutralized(self) -> None:
        assert _sanitize_csv_cell("  =cmd") == "'  =cmd"

    def test_leading_whitespace_then_plus_neutralized(self) -> None:
        assert _sanitize_csv_cell("  +SUM(A1)") == "'  +SUM(A1)"

    def test_numeric_string_unchanged(self) -> None:
        assert _sanitize_csv_cell("42") == "42"

    def test_string_starting_with_equals_in_middle_unchanged(self) -> None:
        assert _sanitize_csv_cell("A=B") == "A=B"

    def test_only_equals_sign_neutralized(self) -> None:
        assert _sanitize_csv_cell("=") == "'="

    def test_only_plus_sign_neutralized(self) -> None:
        assert _sanitize_csv_cell("+") == "'+"

    def test_non_string_input_converted(self) -> None:
        assert _sanitize_csv_cell(123) == "123"  # type: ignore[arg-type]
