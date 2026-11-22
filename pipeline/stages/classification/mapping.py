"""Category consolidation mapping for job classification.

The large alias table is stored in ``pipeline/data/category_mapping.json``.
This module keeps the existing public API while making the mapping data easier
to review and update.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any, Final
from pipeline.infra.paths import PACKAGE_DATA_DIR, runtime_data_dir

logger = logging.getLogger(__name__)

_DATA_PATH = PACKAGE_DATA_DIR / "category_mapping.json"


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

    normalized_category = _strip_region_suffix(category.lower().strip())
    if normalized_category in INVALID_CATEGORIES:
        return None
    mapped = _direct_or_family_category(normalized_category)
    if mapped is not None:
        return mapped
    mapped = _category_without_job_suffix(normalized_category)
    if mapped is not None:
        return mapped
    if _log_unmapped:
        _log_unmapped_category(normalized_category)
    return None


def _strip_region_suffix(category: str) -> str:
    for suffix in ("_apac", "_emea", "_latam", "_na", "_us", "_uk"):
        if category.endswith(suffix):
            return category[: -len(suffix)]
    return category


def _direct_or_family_category(category: str) -> str | None:
    if category in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[category]
    if category in CANONICAL_CATEGORIES:
        return category
    for prefix, canonical in (("legal_", "legal"), ("hr_", "hr"), ("employee_", "hr"), ("patient_", "healthcare"), ("clinical_", "healthcare")):
        if category.startswith(prefix):
            return canonical
    if category.startswith("field_"):
        if "sales" in category:
            return "sales"
        if "care" in category:
            return "healthcare"
    if category.endswith("_sales"):
        return "sales"
    if category.endswith(("_consulting", "_consultant")):
        return "consulting"
    if category.endswith("_training"):
        return "education"
    return None


def _category_without_job_suffix(category: str) -> str | None:
    for suffix in (
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
    ):
        if category.endswith(suffix):
            base = category[: -len(suffix)]
            if base in CATEGORY_MAPPING:
                return CATEGORY_MAPPING[base]
            if base in CANONICAL_CATEGORIES:
                return base

    return None


def _log_unmapped_category(category: str) -> None:
    """Log unmapped categories to JSON for manual review."""
    log_path = runtime_data_dir() / "unmapped_categories.json"
    unmapped = set()
    if log_path.exists():
        try:
            unmapped = set(json.loads(log_path.read_text()))
        except json.JSONDecodeError:
            unmapped = set()

    if category not in unmapped:
        unmapped.add(category)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            log_path.write_text(json.dumps(sorted(unmapped), indent=2))
        except OSError as exc:
            logger.warning("Failed to write unmapped category to %s: %s", log_path, exc)
