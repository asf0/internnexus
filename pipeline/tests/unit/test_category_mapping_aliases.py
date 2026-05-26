from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.classification import get_canonical_category


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


def test_unmapped_values_now_resolve_to_null(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert get_canonical_category("totally_new_category_we_have_never_seen") is None
