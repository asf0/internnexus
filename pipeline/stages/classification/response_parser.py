"""Pure parsing and normalization for classification model output."""

from __future__ import annotations

import json
import re

from pipeline.stages.classification.mapping import get_canonical_category

VALID_CATEGORY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
CANDIDATE_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_\-]+")


def _strip_json_fence(raw_output: str) -> str:
    text = raw_output.strip()
    if text.startswith("```"):
        text = text[3:]
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.lstrip()
        if text.endswith("```"):
            text = text[:-3].rstrip()
    return text.strip()


def _extract_json_category(raw_output: str) -> str | None:
    """Extract category value from JSON output if present."""
    if not raw_output:
        return None

    text = _strip_json_fence(raw_output)

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    category_value = payload.get("category")
    if not isinstance(category_value, str):
        return None
    return _normalize_slug_token(category_value)


def _normalize_slug_token(raw_token: str) -> str | None:
    """Normalize one token candidate into a category-like slug."""
    if not raw_token:
        return None

    category = raw_token.strip().strip("\"'").lower()
    category = re.sub(r"[\s\-]+", "_", category)
    category = re.sub(r"[^a-z0-9_]", "", category)
    category = category.strip("_")
    category = re.sub(r"_+", "_", category)

    if not category or not VALID_CATEGORY_PATTERN.match(category):
        return None
    return category


def _extract_batch_categories(raw_output: str, expected_count: int) -> list[tuple[str | None, str, str]]:
    """Extract ordered batch categories from a JSON array response."""
    if not raw_output or not raw_output.strip():
        return [(None, "empty_response", raw_output)] * expected_count
    payload, error = _batch_payload(raw_output)
    if payload is None:
        return [(None, error, raw_output)] * expected_count
    by_id = _batch_categories_by_id(payload)
    return [_batch_result(by_id.get(str(index)), raw_output) for index in range(expected_count)]


def _batch_payload(raw_output: str) -> tuple[list[object] | None, str]:
    try:
        payload = json.loads(_strip_json_fence(raw_output))
    except json.JSONDecodeError:
        return None, "invalid_json"
    if isinstance(payload, dict):
        payload = next(
            (value for key in ("results", "jobs", "classifications") if isinstance((value := payload.get(key)), list)),
            payload,
        )
    if isinstance(payload, list):
        return payload, ""
    return None, "invalid_json_shape"


def _batch_categories_by_id(payload: list[object]) -> dict[str, str]:
    categories: dict[str, str] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        raw_id, raw_category = item.get("id"), item.get("category")
        normalized = _normalize_slug_token(raw_category) if isinstance(raw_category, str) else None
        if raw_id is not None and normalized:
            categories[str(raw_id)] = normalized
    return categories


def _batch_result(category: str | None, raw_output: str) -> tuple[str | None, str, str]:
    if not category:
        return None, "missing_batch_result", raw_output
    canonical = _map_category_strict(category)
    if canonical:
        return canonical, "ok", raw_output
    return None, "no_mappable_token", raw_output


def _extract_canonical_category(raw_output: str) -> tuple[str | None, str]:
    """Extract the first valid canonical category from model output."""
    if not raw_output or not raw_output.strip():
        return None, "empty_response"

    json_category = _extract_json_category(raw_output)
    if json_category:
        canonical = _map_category_strict(json_category)
        if canonical:
            return canonical, "ok"

    for raw_token in CANDIDATE_TOKEN_PATTERN.findall(raw_output):
        normalized = _normalize_slug_token(raw_token)
        if not normalized:
            continue
        canonical = _map_category_strict(normalized)
        if canonical:
            return canonical, "ok"

    return None, "no_mappable_token"


def _map_category_strict(category: str) -> str | None:
    """Strict category mapping wrapper that suppresses unmapped logging."""
    return get_canonical_category(category, _log_unmapped=False)
