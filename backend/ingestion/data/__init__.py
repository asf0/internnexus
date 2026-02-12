"""Data loader for company information."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Path to the companies JSON file
_COMPANIES_JSON = Path(__file__).parent / "companies.json"


def _load_companies_data() -> dict[str, Any]:
    """Load companies data from JSON file."""
    with open(_COMPANIES_JSON, encoding="utf-8") as f:
        return json.load(f)


def load_common_companies() -> set[str]:
    """Load common company slugs from JSON file.

    Returns:
        Set of company slugs to check for job boards.
    """
    data = _load_companies_data()
    return set(data.get("common_slugs", []))


def load_companies_by_category(category: str) -> set[str]:
    """Load company slugs by category.

    Args:
        category: Category name (e.g., "faang", "startups", "enterprise")

    Returns:
        Set of company slugs for the given category.
    """
    data = _load_companies_data()
    categories = data.get("categories", {})
    return set(categories.get(category, []))


def get_all_categories() -> list[str]:
    """Get list of available company categories.

    Returns:
        List of category names.
    """
    data = _load_companies_data()
    return list(data.get("categories", {}).keys())
