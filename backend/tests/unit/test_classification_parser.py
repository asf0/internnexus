from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.classification import _extract_canonical_category, _normalize_slug_token


def test_normalize_slug_token_accepts_valid_slugs():
    assert _normalize_slug_token("software_engineering") == "software_engineering"
    assert _normalize_slug_token("Software-Engineering") == "software_engineering"


def test_extract_canonical_category_accepts_numbered_output():
    category, reason = _extract_canonical_category("1. software_engineering")
    assert category == "software_engineering"
    assert reason == "ok"


def test_extract_canonical_category_accepts_prefixed_output():
    category, reason = _extract_canonical_category("Category: data_science")
    assert category == "data_science"
    assert reason == "ok"


def test_extract_canonical_category_accepts_multiline_output():
    raw = "The best category is:\nproduct_management\nbecause of roadmap ownership."
    category, reason = _extract_canonical_category(raw)
    assert category == "product_management"
    assert reason == "ok"


def test_extract_canonical_category_rejects_empty():
    category, reason = _extract_canonical_category("   ")
    assert category is None
    assert reason == "empty_response"


def test_extract_canonical_category_rejects_unmappable_text():
    category, reason = _extract_canonical_category("totally_unknown_category_slug")
    assert category is None
    assert reason == "no_mappable_token"
