"""Validated loader for cleanup lookup data."""

from __future__ import annotations

import json
import re
from pathlib import Path


_OVERRIDES_PATH = Path(__file__).parent / "cleanup_overrides.json"
_OVERRIDE_FIELDS = frozenset({"city", "state", "country"})


def _validate_patterns(data: dict[object, object]) -> list[str]:
    patterns = data.get("plain_remote_patterns")
    if not isinstance(patterns, list):
        raise ValueError(f"'plain_remote_patterns' must be a list, got {type(patterns).__name__}")
    for index, pattern in enumerate(patterns):
        if not isinstance(pattern, str):
            raise ValueError(f"Pattern at index {index} must be a string, got {type(pattern).__name__}")
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ValueError(f"Invalid regex at pattern index {index} ({pattern!r}): {exc}") from exc
    return list(patterns)


def _validate_override(key: object, value: object) -> dict[str, str | None]:
    if not isinstance(value, dict):
        raise ValueError(f"Override '{key}' must be a dict, got {type(value).__name__}")
    fields = set(value)
    missing = _OVERRIDE_FIELDS - fields
    if missing:
        raise ValueError(f"Override '{key}' missing fields: {sorted(missing)}")
    extra = fields - _OVERRIDE_FIELDS
    if extra:
        raise ValueError(f"Override '{key}' has unexpected fields: {sorted(extra)}")
    result: dict[str, str | None] = {}
    for field in _OVERRIDE_FIELDS:
        field_value = value[field]
        if field_value is not None and not isinstance(field_value, str):
            raise ValueError(
                f"Override '{key}' field '{field}' must be string or null, got {type(field_value).__name__}"
            )
        result[field] = field_value
    return result


def _validate_overrides(data: dict[object, object]) -> dict[str, dict[str, str | None]]:
    overrides = data.get("location_overrides")
    if not isinstance(overrides, dict):
        raise ValueError(f"'location_overrides' must be a dict, got {type(overrides).__name__}")
    return {key: _validate_override(key, value) for key, value in overrides.items()}


def _load_from_path(path: Path) -> tuple[list[str], dict[str, dict[str, str | None]]]:
    with open(path) as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Top-level JSON must be a dict, got {type(data).__name__}")

    return _validate_patterns(data), _validate_overrides(data)


_PATTERNS, _OVERRIDES = _load_from_path(_OVERRIDES_PATH)
