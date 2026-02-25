"""Category consolidation mapping for job classification.

This module defines the canonical category list and mappings from
LLM-generated variations to consolidated categories.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# Canonical categories
CANONICAL_CATEGORIES = [
    "software_engineering",
    "data_science",
    "data_engineering",
    "machine_learning",
    "product_management",
    "product_design",
    "sales",
    "marketing",
    "operations",
    "finance",
    "hr",
    "customer_success",
    "security",
    "devops",
    "legal",
    "healthcare",
    "research",
    "consulting",
    "project_management",
    "quality_assurance",
    "hardware_engineering",
    "content_writing",
    "translation",
    "education",
    "construction",
    "accounting",
    "compliance",
    "risk_management",
    "recruiting",
    "customer_support",
    "logistics_supply_chain",
]

# Mapping from LLM-generated variations to canonical categories
CATEGORY_MAPPING = {
    # Software Engineering variations
    "engineering": "software_engineering",
    "frontend_engineering": "software_engineering",
    "backend_engineering": "software_engineering",
    "full_stack_engineering": "software_engineering",
    "fullstack_engineering": "software_engineering",
    "full_stack_development": "software_engineering",
    "fullstack_development": "software_engineering",
    "fullstack_developer": "software_engineering",
    "full_stack_developer": "software_engineering",
    "frontend": "software_engineering",
    "frontend_development": "software_engineering",
    "front_end_development": "software_engineering",
    "front_end_developer": "software_engineering",
    "back_end_engineering": "software_engineering",
    "web_engineering": "software_engineering",
    "web_development": "software_engineering",
    "mobile_engineering": "software_engineering",
    "mobile_developer": "software_engineering",
    "android_engineering": "software_engineering",
    "ios_engineering": "software_engineering",
    "game_engineering": "software_engineering",
    "game_development": "software_engineering",
    "game_developer": "software_engineering",
    "game_engineing": "software_engineering",
    "game_engine_development": "software_engineering",
    "ai_engineering": "software_engineering",
    "cloud_engineering": "software_engineering",
    "database_engineering": "software_engineering",
    "product_engineering": "software_engineering",
    "platform_engineering": "software_engineering",
    "production_engineering": "software_engineering",
    "embedded_engineering": "software_engineering",
    "embedded_software_engineering": "software_engineering",
    "embedded_systems": "software_engineering",
    "graphics_engineering": "software_engineering",
    "network_engineering": "software_engineering",
    "systems_engineering": "software_engineering",
    "system_engineering": "software_engineering",
    "site_reliability_engineering": "software_engineering",
    "reliability_engineering": "software_engineering",
    "performance_engineering": "software_engineering",
    "test_engineering": "software_engineering",
    "quality_engineering": "software_engineering",
    "qa_engineering": "software_engineering",
    "support_engineering": "software_engineering",
    "customer_support_engineering": "software_engineering",
    "technical_support_engineering": "software_engineering",
    "sales_engineering": "software_engineering",
    "field_engineering": "software_engineering",
    "solutions_engineering": "software_engineering",
    "integration_engineering": "software_engineering",
    "engineering_services": "software_engineering",
    "digital_engineering": "software_engineering",
    "web3_engineering": "software_engineering",
    "blockchain_engineering": "software_engineering",
    "rust_engineering_blockchain_security": "software_engineering",
    "ui_engineering": "software_engineering",
    "ui_programming": "software_engineering",
    "analytics_engineering": "software_engineering",
    "infrastructure_software_engineering": "software_engineering",
    "technical_engineering": "software_engineering",
    "service_engineering": "software_engineering",
    "professional_services_engineering": "software_engineering",
    "professional_services_engineer": "software_engineering",
    "salesforce_engineering": "software_engineering",
    "salesforce_developer": "software_engineering",
    "hris_and_talent_acquisition_systems_tool_engineer": "software_engineering",
    "cloud_database_engineering": "software_engineering",
    "robotics_engineering": "software_engineering",
    "silicon_engineering": "software_engineering",
    "space_engineering": "software_engineering",
    "manufacturing_engineering": "software_engineering",
    "growth_engineering": "software_engineering",
    "security_software_engineering": "software_engineering",
    "infrastructure_engineer": "software_engineering",
    # DevOps variations
    "devops": "devops",
    "dev_ops": "devops",
    "dev_ops_engineering": "devops",
    "devops_engineering": "devops",
    "infrastructure_engineering": "devops",
    "cloud_operations": "devops",
    "cloud_computing": "devops",
    "cloud_architecture": "devops",
    "cloud_networking": "devops",
    "system_administration": "devops",
    "deployment_strategist": "devops",
    # Hardware Engineering
    "hardware_engineering": "hardware_engineering",
    "mechanical_engineering": "hardware_engineering",
    "electrical_engineering": "hardware_engineering",
    "engineering_mechanical": "hardware_engineering",
    "mechanical_design": "hardware_engineering",
    "materials_engineering": "hardware_engineering",
    "civil_engineering": "hardware_engineering",
    "construction_engineering": "hardware_engineering",
    "validation_engineering": "hardware_engineering",
    # Data Science variations
    "data_analysis": "data_science",
    "data_analytics": "data_science",
    "data_scientist": "data_science",
    "business_analysis": "data_science",
    "business_analytics": "data_science",
    "business_intelligence": "data_science",
    "business_intelligence_analysis": "data_science",
    "business_systems_analysis": "data_science",
    "business_solutions_analysis": "data_science",
    "product_analysis": "data_science",
    "product_data_analysis": "data_science",
    "product_data_science": "data_science",
    "data_science_ml": "data_science",
    "data_strategy": "data_science",
    "data_governance": "data_science",
    "data_management": "data_science",
    "data_privacy": "data_science",
    "data_architecture": "data_science",
    "data_center_management": "data_science",
    "data_center_coordinator": "data_science",
    "data_entry": "data_science",
    "data_law": "data_science",
    "data_operations": "data_science",
    "analytics": "data_science",
    # Data Engineering variations
    "data_engineering_software": "data_engineering",
    # Machine Learning variations
    "ml_engineering": "machine_learning",
    "ml_engineer": "machine_learning",
    # Product Management variations
    "product": "product_management",
    "product_strategy": "product_management",
    "product_strategy_management": "product_management",
    "technical_program_management": "product_management",
    "technical_project_management": "product_management",
    "product_operations": "product_management",
    "product_development": "product_management",
    "product_support": "product_management",
    # Product Design variations
    "design": "product_design",
    "ux_design": "product_design",
    "ui_design": "product_design",
    "uiux_design": "product_design",
    "ux_ui_design": "product_design",
    "graphic_design": "product_design",
    "game_design": "product_design",
    "designer": "product_design",
    "designer_entry_level": "product_design",
    "designer_remote": "product_design",
    "designers_brand": "product_design",
    "web_design": "product_design",
    "systems_design": "product_design",
    "technical_design": "product_design",
    "content_design": "product_design",
    "design_operations": "product_design",
    "animation": "product_design",
    # Sales variations
    "sales_management": "sales",
    "sales_marketing": "sales",
    "sales_and_service_management": "sales",
    "sales_and_service_lead": "sales",
    "sales_development": "sales",
    "sales_sales_development": "sales",
    "sales_business_development": "sales",
    "sales_enablement_manager": "sales",
    "sales_director": "sales",
    "sales_and_marketing": "sales",
    "consultant_sales": "sales",
    "freelance_sales": "sales",
    "inside_sales": "sales",
    "account_management": "sales",
    "account_executive": "sales",
    "technical_account_management": "sales",
    "client_services": "sales",
    "client_success": "sales",
    "client_success_management": "sales",
    # Marketing variations
    "growth_marketing": "marketing",
    "product_marketing": "marketing",
    "digital_marketing": "marketing",
    "content_marketing": "marketing",
    "marketing_operations": "marketing",
    "technical_marketing": "marketing",
    "management_marketing": "marketing",
    "marketing_science": "marketing",
    "freelance_marketing": "marketing",
    "seo_specialist": "marketing",
    "seo_strategist": "marketing",
    # Operations variations
    "operation": "operations",
    "operations_management": "operations",
    "business_operations": "operations",
    "engineering_operations": "operations",
    "manufacturing_operations": "operations",
    "finance_operations": "operations",
    "healthcare_operations": "operations",
    "healthcare_ops": "operations",
    "medical_operations": "operations",
    "security_operations": "operations",
    "recruitment_operations": "operations",
    "customer_service_operations": "operations",
    "customer_success_operations": "operations",
    "sales_operations": "sales",  # Maps to sales
    "hr_operations": "hr",  # Maps to HR
    "education_operations": "education",  # Maps to education
    "training_operations": "education",
    "data_collection_operations": "operations",
    "installation_operations": "operations",
    "production_operations": "operations",
    "construction_operations": "construction",
    "technical_operations": "operations",
    "management_operations": "operations",
    "remote_management": "operations",
    "service_management": "operations",
    "production_management": "operations",
    "coffee_shop_operations": "operations",
    "start_up_operations": "operations",
    "web_management": "operations",
    "technology_management": "operations",
    "management": "operations",
    "business_management": "operations",
    "finance_management": "finance",
    "security_management": "security",
    "risk_management": "risk_management",
    "supply_chain_management": "logistics_supply_chain",
    "construction_management": "construction",
    "event_management": "operations",
    "infrastructure_management": "devops",
    "governance_risk_compliance": "operations",
    "governance_risk_control": "operations",
    "risk_compliance": "operations",
    "e_commerce_management": "operations",
    "ecommerce_management": "operations",
    "virtual_healthcare": "healthcare",
    "telemedicine_operations": "healthcare",
    "medtech_operations": "healthcare",
    "travel_healthcare": "healthcare",
    "virtual_urgent_care": "healthcare",
    "physical_treatment_operations": "healthcare",
    "physical_treatment": "healthcare",
    "web3_operations": "operations",
    "medical_finance": "finance",
    "law_finance": "finance",
    "security_finance": "finance",
    "healthcare_finance": "finance",
    "engineering_management": "software_engineering",
    "engineering_management_ai_platform": "software_engineering",
    "engineering_director": "software_engineering",
    "management_engineering": "software_engineering",
    "tech_leadership": "operations",
    "technical_management": "operations",
    "management_technology": "operations",
    "technology_enabled_finance_transformation": "finance",
    "entrepreneurship_internal_operations": "operations",
    "gtm_operations": "operations",
    "rev_ops": "operations",
    # Finance variations
    "accounting": "accounting",
    "accounting_operations": "finance",
    "finance_and_strategy": "finance",
    "finance_business_development": "finance",
    "finance_events_volunteer": "finance",
    "procurement": "operations",
    # Accounting variations
    "accountant": "accounting",
    "account_associate": "accounting",
    "accounting_consultant": "accounting",
    "accounting_controller": "accounting",
    "accounting_supervision": "accounting",
    "accounting_supervisor": "accounting",
    "accounting_and_tax_specialist": "accounting",
    "accounting_and_consolidation_specialist": "accounting",
    "technical_accounting": "accounting",
    # Compliance variations
    "compliance": "compliance",
    "compliance_analyst": "compliance",
    "compliance_consulting": "compliance",
    "compliance_inspection": "compliance",
    "compliance_investigation": "compliance",
    "compliance_management": "compliance",
    "governance_and_compliance": "compliance",
    "regulatory_compliance": "compliance",
    "payroll_compliance": "compliance",
    # Risk variations
    "risk_analysis": "risk_management",
    "risk_operations": "risk_management",
    "risk_specialist": "risk_management",
    "risk_administration": "risk_management",
    "risk_adjustment": "risk_management",
    "remote_risk_specialist": "risk_management",
    "security_risk_management": "risk_management",
    # Recruiting variations
    "junior_recruiter": "recruiting",
    "healthcare_recruiter": "recruiting",
    "talent_sourcing": "recruiting",
    "senior_talent_partner": "recruiting",
    # Customer support variations
    "customer_support": "customer_support",
    "client_support": "customer_support",
    "application_support": "customer_support",
    "desktop_support_analyst": "customer_support",
    "development_support": "customer_support",
    "operations_support": "customer_support",
    "operations_support_specialist": "customer_support",
    "social_media_support": "customer_support",
    "support_specialist": "customer_support",
    # Logistics and supply chain variations
    "logistics": "logistics_supply_chain",
    "logistics_analysis": "logistics_supply_chain",
    "global_logistics_specialist": "logistics_supply_chain",
    "supply_chain_operations": "logistics_supply_chain",
    "supply_chain_specialist": "logistics_supply_chain",
    # HR variations
    "human_resources": "hr",
    "talent_acquisition": "hr",
    "recruiting": "recruiting",
    "recruitment": "hr",
    "recruitment_management": "hr",
    "recruitment_coordinator": "hr",
    "recruitment_and_hr_operations": "hr",
    "hr_business_partner": "hr",
    "hr_sales_operations": "hr",
    "hr_payroll_operations": "hr",
    "payroll": "finance",
    "payroll_associate": "finance",
    "payroll_specialist": "finance",
    "hr_data_engineering": "hr",
    "people_operations": "hr",
    "learning_and_development": "hr",
    # Customer Success variations
    "customer_service": "customer_success",
    "customer_support_management": "customer_success",
    "customer_success_management": "customer_success",
    "customer_experience": "customer_success",
    "customer_enablement_architect": "customer_success",
    "technical_support": "customer_success",
    "technical_support_engineer": "customer_success",
    "it_support": "customer_success",
    "support_specialist_german_speaking": "customer_success",
    "production_support": "customer_success",
    # Security variations
    "information_security": "security",
    "cyber_security": "security",
    "cybersecurity": "security",
    "data_security": "security",
    "cloud_security": "security",
    "network_security": "security",
    "infrastructure_security": "security",
    "infrastructure_security_engineering": "security",
    "product_security": "security",
    "security_analysis": "security",
    "security_research": "security",
    "security_national_security": "security",
    "information_security_and_grc": "security",
    # Legal variations
    "law": "legal",
    "lawyer": "legal",
    "legal_operations": "legal",
    "legal_services": "legal",
    "legal_contracts": "legal",
    "legal_technology": "legal",
    "legal_and_compliance": "legal",
    "legal_business_development": "legal",
    "law_business_development": "legal",
    "law_operations": "legal",
    "regulatory_affairs": "legal",
    # Healthcare variations
    "healthcare_management": "healthcare",
    "clinical_management": "healthcare",
    "clinical_research": "healthcare",
    "clinical_pharmacy": "healthcare",
    "medical_research": "healthcare",
    "medical_healthcare": "healthcare",
    "nursing_nurse_management": "healthcare",
    "healthcare_nursing": "healthcare",
    "nurse_practitioner": "healthcare",
    "environmental_health_and_safety": "healthcare",
    "environmental_health_and_safety_technician": "healthcare",
    "medtech_rim": "healthcare",
    # Research variations
    "research": "research",
    "research_science": "research",
    "research_engineering": "research",
    "research_and_development": "research",
    "materials_research_and_development": "research",
    # Consulting variations
    "consultant": "consulting",
    "consultant_integration": "consulting",
    "consultant_patient_analytics": "consulting",
    "business_consulting": "consulting",
    "technology_consulting": "consulting",
    "technical_consulting": "consulting",
    "professional_services": "consulting",
    "environmental_consulting": "consulting",
    "shipping": "operations",
    "shipping_operations": "operations",
    # Project Management variations
    "project_manager": "project_management",
    "program_manager": "project_management",
    "technical_program_manager": "project_management",
    "staff_technical_program_manager": "project_management",
    "remote_project_management": "project_management",
    "localization_project_management": "project_management",
    "construction_project_management": "construction",
    "event_coordinator_volunteer": "project_management",
    "event_volunteering": "project_management",
    # Quality Assurance variations
    "testing": "quality_assurance",
    "quality_control": "quality_assurance",
    "quality_assurance": "quality_assurance",
    "ai_testing": "quality_assurance",
    "ai_testing_french_language": "quality_assurance",
    "localization_tester": "quality_assurance",
    # Content Writing variations
    "technical_writing": "content_writing",
    "technical_writing_management": "content_writing",
    "content_writing": "content_writing",
    "academic_content_specialist": "content_writing",
    "creative_annotating": "content_writing",
    # Translation variations
    "language_translator": "translation",
    "language_translations": "translation",
    "language_linguist": "translation",
    "translation_quality_reviewing": "translation",
    "translation_quality_rater": "translation",
    "translation_quality_reviewer": "translation",
    "translation_and_localization": "translation",
    # Education variations
    "education_training": "education",
    "training": "education",
    "technical_training": "education",
    "training_and_education": "education",
    "instructional_design": "education",
    "instructional_designer": "education",
    "instructional_designing": "education",
    "instructional_designing_and_lms_administration": "education",
    "professional_learning_specialist": "education",
    "volunteer_programme": "education",
    # Construction variations
    "construction": "construction",
    # Problematic categories to fix
    "none": None,  # Should be NULL
    "space_x": None,  # Company name
    "space_x_operations": None,  # Company name
    "space_programming": None,  # Invalid
    "category": None,
    "test": None,
    "tester": None,
    "the": None,
    "m": None,
    "totally_unknown_category_slug": None,
    "gis_mapper": "operations",  # Ambiguous - map to operations
    "gis_mapping": "operations",
    "studio_recording_project": "content_writing",  # Media/content
    "studio_recording": "content_writing",
    "audio_recording_project": "content_writing",
    "voice_talent": "content_writing",
    "video_production": "content_writing",
    # Field data collection
    "data_collection": "operations",
    "field_data_collection": "operations",
    "data_verification_assistant": "operations",
    "configuration_technical_setup_specialist": "operations",
    "configuration_and_technical_setup_specialist": "operations",
    "technical_field_specialist": "operations",
    # Developer relations
    "developer_relations": "software_engineering",
    "developer_advocacy": "software_engineering",
    # Architecture
    "architecture": "software_engineering",
    "enterprise_architecture": "software_engineering",
    "project_architect": "software_engineering",
    # Leadership
    "leadership": "operations",
    "leadership_advisor": "operations",
    "technical_leader": "operations",
    # Venture capital
    "venture_capital": "finance",
    # Installation
    "installation": "operations",
    # Real estate
    "real_estate": "operations",
    # AWS program
    "aws_program": "software_engineering",
    # Cloudinary
    "cloudinary": "software_engineering",
    # Knowledge management
    "knowledge_management": "operations",
    # Mainframe
    "mainframe_systems_programming": "software_engineering",
    # Partner enablement
    "partner_enablement_management": "operations",
    # Technology entry level
    "technology_entry_level": "software_engineering",
    # Freelance court reporting
    "freelance_court_reporting": "legal",
    # Guest experience
    "guest_experience_management": "operations",
}

# Categories that should be set to NULL (invalid/problematic)
INVALID_CATEGORIES = {
    "none",
    "space_x",
    "space_x_operations",
    "space_programming",
}


def get_canonical_category(category: str | None) -> str | None:
    """Map a category to its canonical form.

    Args:
        category: The original category string

    Returns:
        The canonical category, or None if the category should be null
    """
    if not category:
        return None

    category_lower = category.lower().strip()

    # Check if it's an invalid category
    if category_lower in INVALID_CATEGORIES:
        return None

    # Check direct mapping
    if category_lower in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[category_lower]

    # Check if already canonical
    if category_lower in CANONICAL_CATEGORIES:
        return category_lower

    # Try to find a match by removing common suffixes
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
        if category_lower.endswith(suffix):
            base = category_lower[: -len(suffix)]
            if base in CATEGORY_MAPPING:
                return CATEGORY_MAPPING[base]
            if base in CANONICAL_CATEGORIES:
                return base

    # Unknown categories are kept NULL and logged for curation.
    _log_unmapped_category(category_lower)
    return None


def _log_unmapped_category(category: str):
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
    """Get all variations grouped by canonical category.

    Returns:
        Dict mapping canonical categories to lists of variations
    """
    variations: dict[str, list[str]] = {cat: [] for cat in CANONICAL_CATEGORIES}

    for original, canonical in CATEGORY_MAPPING.items():
        if canonical and canonical in variations:
            variations[canonical].append(original)

    return variations


def validate_category(category: str | None) -> bool:
    """Check if a category is valid (canonical or mappable).

    Args:
        category: The category to validate

    Returns:
        True if the category is valid or can be mapped
    """
    if not category:
        return True  # NULL is valid

    canonical = get_canonical_category(category)
    return canonical is not None
