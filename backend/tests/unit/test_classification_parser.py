from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.classification import (
    _extract_canonical_category,
    _map_category_strict,
    _normalize_slug_token,
)


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


def test_extract_canonical_category_accepts_json_output():
    category, reason = _extract_canonical_category('{"category":"software_engineering"}')
    assert category == "software_engineering"
    assert reason == "ok"


def test_extract_canonical_category_accepts_fenced_json_output():
    raw = """```json
    {"category":"product_management"}
    ```"""
    category, reason = _extract_canonical_category(raw)
    assert category == "product_management"
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


def test_map_category_strict_handles_common_short_aliases():
    assert _map_category_strict("sre") == "software_engineering"
    assert _map_category_strict("hrbp") == "hr"
    assert _map_category_strict("welder") == "construction"
    assert _map_category_strict("roofing") == "construction"


def test_map_category_strict_handles_recent_rejection_aliases():
    assert _map_category_strict("store_operations") == "operations"
    assert _map_category_strict("trade_marketing") == "marketing"
    assert _map_category_strict("security_consulting") == "security"
    assert _map_category_strict("operationsfinance") == "finance"
    assert _map_category_strict("paid_growth_strategist") == "marketing"


def test_map_category_strict_handles_latest_tail_aliases():
    assert _map_category_strict("business_development") == "sales"
    assert _map_category_strict("legal_counselling") == "legal"
    assert _map_category_strict("user_experience_design") == "product_design"
    assert _map_category_strict("toolmaking") == "construction"


def test_map_category_strict_handles_recent_long_tail_aliases():
    assert _map_category_strict("communications_associate") == "marketing"
    assert _map_category_strict("supply_planning_analyst") == "finance"
    assert _map_category_strict("food_safety_management") == "operations"
    assert _map_category_strict("director_clinical_research") == "healthcare"
    assert _map_category_strict("fulfillment_team_member") == "logistics_supply_chain"
    assert _map_category_strict("telecom_sales_specialist") == "sales"
    assert _map_category_strict("billing_and_revenue_management") == "finance"
    assert _map_category_strict("aml_investigation") == "compliance"
    assert _map_category_strict("customer_enablement") == "customer_success"
    assert _map_category_strict("hr_specialist") == "hr"


def test_map_category_strict_handles_latest_run_tail_aliases():
    assert _map_category_strict("government_sales") == "sales"
    assert _map_category_strict("global_account_executive") == "sales"
    assert _map_category_strict("graphic_designer") == "marketing"
    assert _map_category_strict("media_management") == "marketing"
    assert _map_category_strict("medical_director_veterinarian") == "healthcare"
    assert _map_category_strict("proposal_coordinator") == "project_management"
    assert _map_category_strict("java_backend_development") == "software_engineering"
    assert _map_category_strict("javascript_development") == "software_engineering"
    assert _map_category_strict("test_automation_development") == "quality_assurance"
    assert _map_category_strict("mlro_deputy_mlo") == "compliance"
    assert _map_category_strict("employee_relations") == "hr"
    assert _map_category_strict("remote_virtual_assistant") == "operations"


def test_map_category_strict_handles_final_long_tail_aliases():
    assert _map_category_strict("legal_administrative_assistant") == "legal"
    assert _map_category_strict("legal_administrative_support") == "legal"
    assert _map_category_strict("value_engineering") == "consulting"
    assert _map_category_strict("paid_media_director") == "marketing"
    assert _map_category_strict("application_security_consulting") == "security"
    assert _map_category_strict("risk_analytics") == "risk_management"
    assert _map_category_strict("mainframe_development") == "software_engineering"
    assert _map_category_strict("ux_research") == "product_design"
    assert _map_category_strict("finance_director_emea") == "finance"


def test_map_category_strict_applies_family_rules_and_suffix_normalization():
    assert _map_category_strict("field_sales") == "sales"
    assert _map_category_strict("solution_consulting") == "consulting"
    assert _map_category_strict("forensics_training") == "education"
    assert _map_category_strict("patient_support") == "healthcare"
    assert _map_category_strict("hr_shared_services") == "hr"
    assert _map_category_strict("community_management") == "operations"


def test_map_category_strict_handles_market_alignment_aliases():
    assert _map_category_strict("gtm_enablement") == "sales"
    assert _map_category_strict("global_immigration_compliance") == "compliance"
    assert _map_category_strict("compliance_program_management") == "compliance"
    assert _map_category_strict("executive_recruiting") == "recruiting"
    assert _map_category_strict("data_protection") == "security"
    assert _map_category_strict("embedded_studio_management") == "operations"
    assert _map_category_strict("payments_partnerships_manager") == "finance"
    assert _map_category_strict("field_testing") == "quality_assurance"
    assert _map_category_strict("public_sector_contract_strategy") == "legal"
    assert _map_category_strict("media_planning") == "marketing"


def test_map_category_strict_handles_latest_rejection_tail_aliases():
    assert _map_category_strict("director_of_talent_acquisition") == "recruiting"
    assert _map_category_strict("aml_analysis") == "compliance"
    assert _map_category_strict("field_care_coordinator") == "healthcare"
    assert _map_category_strict("arquitecto_de_soluciones") == "software_engineering"
    assert _map_category_strict("lider_tecnico_java") == "software_engineering"
    assert _map_category_strict("finance_specialist") == "finance"
    assert _map_category_strict("finance_accounting") == "finance"
    assert _map_category_strict("automotive_service_manager") == "operations"
    assert _map_category_strict("maintenance_management") == "operations"
    assert _map_category_strict("growth_analysis") == "marketing"
    assert _map_category_strict("voice_coaching") == "education"
