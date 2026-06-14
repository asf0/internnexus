"""Category consolidation mapping for job classification.

The large alias table is stored in ``pipeline/data/category_mapping.json``.
This module keeps the existing public API while making the mapping data easier
to review and update.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "category_mapping.json"


@lru_cache(maxsize=1)
def _load_mapping_data() -> dict[str, Any]:
    with _DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _required(name: str) -> Any:
    data = _load_mapping_data()
    if name not in data:
        raise KeyError(f"Missing category mapping data key: {name}")
    return data[name]


CANONICAL_CATEGORIES: Final[list[str]] = list(_required("canonical_categories"))
CATEGORY_MAPPING: Final[dict[str, str | None]] = dict(_required("category_mapping"))
INVALID_CATEGORIES: Final[set[str]] = set(_required("invalid_categories"))


def get_canonical_category(category: str | None, _log_unmapped: bool = True) -> str | None:
    """Map a category to its canonical form."""
    if not category:
        return None

    category_lower = category.lower().strip()
    normalized_category = category_lower

    if category_lower in INVALID_CATEGORIES:
        return None

    for region_suffix in ["_apac", "_emea", "_latam", "_na", "_us", "_uk"]:
        if category_lower.endswith(region_suffix):
            normalized_category = category_lower[: -len(region_suffix)]
            break

    if normalized_category in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[normalized_category]

    if normalized_category in CANONICAL_CATEGORIES:
        return normalized_category

    # Family/prefix rules previously only in service._map_category_strict.
    for prefix, canonical in (
        ("legal_", "legal"),
        ("hr_", "hr"),
        ("employee_", "hr"),
        ("patient_", "healthcare"),
        ("clinical_", "healthcare"),
    ):
        if normalized_category.startswith(prefix):
            return canonical

    if normalized_category.startswith("field_") and "sales" in normalized_category:
        return "sales"
    if normalized_category.startswith("field_") and "care" in normalized_category:
        return "healthcare"
    if normalized_category.endswith("_sales"):
        return "sales"
    if normalized_category.endswith("_consulting") or normalized_category.endswith("_consultant"):
        return "consulting"
    if normalized_category.endswith("_training"):
        return "education"

    for suffix in [
        "_engineering",
        "_management",
        "_operations",
        "_development",
        "_analysis",
        "_administrator",
        "_manager",
        "_executive",
        "_consulting",
        "_advisory",
        "_specialist",
        "_coordinator",
        "_director",
        "_lead",
        "_officer",
        "_assistant",
    ]:
        if normalized_category.endswith(suffix):
            base = normalized_category[: -len(suffix)]
            if base in CATEGORY_MAPPING:
                return CATEGORY_MAPPING[base]
            if base in CANONICAL_CATEGORIES:
                return base

    if _log_unmapped:
        _log_unmapped_category(normalized_category)
    return None


def _log_unmapped_category(category: str) -> None:
    """Log unmapped categories to JSON for manual review."""
    log_path = Path(os.getenv("DATA_DIR", "data")) / "unmapped_categories.json"
    unmapped = set()
    if log_path.exists():
        try:
            unmapped = set(json.loads(log_path.read_text()))
        except json.JSONDecodeError:
            unmapped = set()

    if category not in unmapped:
        unmapped.add(category)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps(sorted(unmapped), indent=2))


def get_all_category_variations() -> dict[str, list[str]]:
    """Get all variations grouped by canonical category."""
    variations: dict[str, list[str]] = {cat: [] for cat in CANONICAL_CATEGORIES}

    for original, canonical in CATEGORY_MAPPING.items():
        if canonical and canonical in variations:
            variations[canonical].append(original)

    return variations


def validate_category(category: str | None) -> bool:
    """Check if a category is valid (canonical or mappable)."""
    if not category:
        return True

    canonical = get_canonical_category(category)
    return canonical is not None
