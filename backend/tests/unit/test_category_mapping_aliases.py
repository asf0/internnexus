from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.category_mapping import get_canonical_category


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
