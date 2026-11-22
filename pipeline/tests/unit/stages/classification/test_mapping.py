from __future__ import annotations

from pipeline.tests.paths import PROJECT_ROOT
import sys
from pathlib import Path

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.stages.classification import get_canonical_category


def test_professional_services_engineer_maps_to_software_engineering():
    assert get_canonical_category("professional_services_engineer") == "software_engineering"


def test_shipping_maps_to_operations():
    assert get_canonical_category("shipping") == "operations"
    assert get_canonical_category("shipping_operations") == "operations"


def test_payroll_associate_maps_to_finance():
    assert get_canonical_category("payroll_associate") == "finance"
    assert get_canonical_category("payroll") == "finance"
    assert get_canonical_category("payroll_specialist") == "finance"


def test_none_stays_invalid():
    assert get_canonical_category("none") is None
    assert get_canonical_category("None") is None


def test_new_canonical_categories_map_correctly():
    assert get_canonical_category("accountant") == "accounting"
    assert get_canonical_category("compliance_analyst") == "compliance"
    assert get_canonical_category("risk_analysis") == "risk_management"
    assert get_canonical_category("talent_sourcing") == "recruiting"
    assert get_canonical_category("application_support") == "customer_support"
    assert get_canonical_category("supply_chain_specialist") == "logistics_supply_chain"


def test_data_backed_occupational_categories_map_correctly():
    assert get_canonical_category("executive_assistant") == "administrative"
    assert get_canonical_category("claims_adjuster") == "insurance"
    assert get_canonical_category("news_producer") == "media_production"
    assert get_canonical_category("video_production") == "media_production"
    assert get_canonical_category("restaurant_management") == "hospitality"
    assert get_canonical_category("property_management") == "real_estate"


def test_latest_single_job_rejection_aliases_map_to_existing_categories():
    assert get_canonical_category("support") == "customer_support"
    assert get_canonical_category("telecommunications") == "hardware_engineering"
    assert get_canonical_category("manufacturing") == "hardware_engineering"
    assert get_canonical_category("revenue_operations") == "operations"


def test_latest_pipeline_rejection_aliases_map_to_existing_categories():
    assert get_canonical_category("agriculture") == "operations"
    assert get_canonical_category("automotive") == "operations"
    assert get_canonical_category("community_service") == "operations"
    assert get_canonical_category("human_engineering") == "hr"
    assert get_canonical_category("people_ops") == "hr"
    assert get_canonical_category("retail") == "operations"
    assert get_canonical_category("sports") == "operations"
    assert get_canonical_category("surveying") == "construction"


def test_unmapped_values_now_resolve_to_null(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert get_canonical_category("totally_new_category_we_have_never_seen") is None


def test_category_mapping_json_targets_valid_canonical_categories():
    import json

    from pipeline.stages.classification.mapping import (
        CANONICAL_CATEGORIES,
        CATEGORY_MAPPING,
        INVALID_CATEGORIES,
        _DATA_PATH,
    )

    data = json.loads(_DATA_PATH.read_text())

    assert data["canonical_categories"] == CANONICAL_CATEGORIES
    assert set(data["invalid_categories"]) == INVALID_CATEGORIES
    assert CATEGORY_MAPPING

    canonical = set(CANONICAL_CATEGORIES)
    invalid_targets = {
        alias: target for alias, target in CATEGORY_MAPPING.items() if target is not None and target not in canonical
    }
    assert invalid_targets == {}
