"""Tests for cleanup/data/loader.py — validated JSON loader for cleanup lookup data."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from pipeline.stages.cleanup import location_parser as parser_mod
from pipeline.stages.cleanup.data import loader as loader_mod


class TestLoadCommittedData:
    """Verify the real committed JSON loads without errors and has expected shape."""

    def test_loads_without_error(self):
        assert isinstance(loader_mod._PATTERNS, list)
        assert isinstance(loader_mod._OVERRIDES, dict)

    def test_patterns_count_and_types(self):
        assert len(loader_mod._PATTERNS) == 7
        for p in loader_mod._PATTERNS:
            assert isinstance(p, str)
            re.compile(p)

    def test_overrides_count_and_types(self):
        assert len(loader_mod._OVERRIDES) == 7
        for key, value in loader_mod._OVERRIDES.items():
            assert isinstance(key, str)
            assert isinstance(value, dict)
            assert set(value.keys()) == {"city", "state", "country"}
            for field in ("city", "state", "country"):
                assert value[field] is None or isinstance(value[field], str)


class TestConstantsMatchPrevious:
    """Module-level constants in parser.py must exactly match previously hardcoded values."""

    def test_plain_remote_patterns_match(self):
        expected = [
            r"^remote$",
            r"^work from home$",
            r"^wfh$",
            r"^distributed$",
            r"^virtual$",
            r"^telecommute$",
            r"^anywhere$",
        ]
        assert parser_mod.PLAIN_REMOTE_PATTERNS == expected

    def test_location_overrides_match(self):
        expected = {
            "mountain view": {"city": "Mountain View", "state": None, "country": "United States"},
            "singapore": {"city": "Singapore", "state": None, "country": "Singapore"},
            "belgrade": {"city": "Belgrade", "state": None, "country": "Serbia"},
            "mexico city": {"city": "Mexico City", "state": None, "country": "Mexico"},
            "vancouver": {"city": "Vancouver", "state": None, "country": "Canada"},
            "nyc": {"city": "New York", "state": "New York", "country": "United States"},
            "sf": {"city": "San Francisco", "state": "California", "country": "United States"},
        }
        assert parser_mod.LOCATION_OVERRIDES == expected


def test_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        loader_mod._load_from_path(tmp_path / "nope.json")


# (case id, file contents, expected exception, message fragment)
MALFORMED = [
    ("malformed_json", "not json", json.JSONDecodeError, ""),
    ("non_dict_top_level", "[1, 2, 3]", ValueError, "must be a dict"),
    ("missing_patterns_key", '{"location_overrides": {}}', ValueError, "plain_remote_patterns"),
    ("missing_overrides_key", '{"plain_remote_patterns": []}', ValueError, "location_overrides"),
    (
        "patterns_not_list",
        '{"plain_remote_patterns": "not a list", "location_overrides": {}}',
        ValueError,
        "plain_remote_patterns",
    ),
    (
        "overrides_not_dict",
        '{"plain_remote_patterns": [], "location_overrides": "not a dict"}',
        ValueError,
        "location_overrides",
    ),
    (
        "invalid_regex",
        '{"plain_remote_patterns": ["^remote$", "[invalid"], "location_overrides": {}}',
        ValueError,
        "Invalid regex",
    ),
    ("pattern_not_string", '{"plain_remote_patterns": [42], "location_overrides": {}}', ValueError, "must be a string"),
    (
        "override_not_dict",
        '{"plain_remote_patterns": [], "location_overrides": {"bad": "not a dict"}}',
        ValueError,
        "must be a dict",
    ),
    (
        "override_missing_fields",
        '{"plain_remote_patterns": [], "location_overrides": {"bad": {"city": "X"}}}',
        ValueError,
        "missing fields",
    ),
    (
        "override_extra_fields",
        '{"plain_remote_patterns": [], "location_overrides": '
        '{"bad": {"city": "X", "state": null, "country": null, "extra": 1}}}',
        ValueError,
        "unexpected fields",
    ),
    (
        "override_wrong_field_type",
        '{"plain_remote_patterns": [], "location_overrides": '
        '{"bad": {"city": 123, "state": null, "country": null}}}',
        ValueError,
        "must be string or null",
    ),
]


@pytest.mark.parametrize(
    ("contents", "exc_type", "match"),
    [(c, e, m) for _id, c, e, m in MALFORMED],
    ids=[case[0] for case in MALFORMED],
)
def test_loader_rejects_malformed(tmp_path, contents, exc_type, match):
    bad = tmp_path / "bad.json"
    bad.write_text(contents)
    with pytest.raises(exc_type, match=match or None):
        loader_mod._load_from_path(bad)
