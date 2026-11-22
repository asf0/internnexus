"""Prompt construction helpers for job classification."""

from __future__ import annotations

import json

from pipeline.stages.classification.mapping import CANONICAL_CATEGORIES

MAX_DESCRIPTION_LENGTH = 500

CATEGORY_HINTS: dict[str, str] = {
    "software_engineering": "backend frontend full_stack api platform",
    "data_science": "analytics experimentation modeling insights statistics",
    "data_engineering": "etl pipelines warehousing spark airflow",
    "machine_learning": "ml ai model_training inference llm",
    "product_management": "roadmap prioritization requirements stakeholders",
    "product_design": "ux ui interaction visual design",
    "sales": "account_executive bdr quota pipeline gtm",
    "marketing": "brand growth campaign paid_media seo",
    "operations": "process execution coordination service_delivery business_ops revenue_ops",
    "finance": "fp_and_a budgeting revenue accounting_strategy",
    "hr": "people_ops talent_acquisition employee_relations",
    "customer_success": "onboarding retention adoption account_health",
    "security": "application_security infosec cyber risk controls",
    "devops": "infra deployment ci_cd sre reliability",
    "legal": "counsel contracts compliance legal_ops",
    "healthcare": "clinical patient_care nursing medical",
    "research": "r_and_d scientific_research lab",
    "consulting": "advisory professional_services implementation",
    "project_management": "program_management delivery planning pmo",
    "quality_assurance": "qa testing validation test_automation",
    "hardware_engineering": "electrical mechanical firmware manufacturing",
    "content_writing": "writing editorial content technical_writing",
    "translation": "localization linguist translation",
    "education": "training instructional learning enablement",
    "construction": "field_construction trades site_ops",
    "accounting": "bookkeeping close gl ar ap",
    "compliance": "regulatory aml kyc controls monitoring",
    "risk_management": "risk assessment governance mitigation",
    "recruiting": "recruiter sourcing interviewing hiring",
    "customer_support": "helpdesk support tickets troubleshooting",
    "logistics_supply_chain": "fulfillment warehouse logistics procurement",
    "administrative": "administrative_assistant executive_assistant office reception",
    "insurance": "underwriting claims adjustment actuarial insurance_policies",
    "media_production": "journalism reporting broadcast video audio production",
    "hospitality": "hotel restaurant chef food_service guest_services",
    "real_estate": "property_management leasing realtor real_estate",
}

VALID_CATEGORIES = CANONICAL_CATEGORIES


def _build_category_cards() -> str:
    """Render compact category cards with keyword hints."""
    cards = []
    for slug in VALID_CATEGORIES:
        hints = CATEGORY_HINTS.get(slug, slug.replace("_", " "))
        cards.append(f"- {slug}: {hints}")
    return "\n".join(cards)


def _truncate_description(description: str) -> str:
    truncated_desc = description[:MAX_DESCRIPTION_LENGTH]
    if len(description) > MAX_DESCRIPTION_LENGTH:
        truncated_desc += "..."
    return truncated_desc


def _build_classification_prompts(title: str, description: str) -> tuple[str, str]:
    """Build deterministic system/user prompts for classification."""
    truncated_desc = _truncate_description(description)

    system_prompt = """You classify job postings into exactly one allowed category slug.
Rules:
- Prefer the title and responsibilities over company industry
- Classify the job function, not its industry or workplace. Labels such as retail,
  automotive, sports, agriculture, or people operations are not allowed slugs; map
  them to the nearest job-function category instead.
- Ignore benefits, EEO/legal text, compensation boilerplate, location, and company marketing
- Return JSON only: {"category":"<allowed_slug>"}
- category must be one slug from the allowed list
- Never invent or transform a new slug
- If uncertain, choose the nearest allowed slug"""

    user_prompt = f"""Allowed categories:
{_build_category_cards()}

Title: {title}
Description: {truncated_desc}

Return JSON only, example: {{"category":"software_engineering"}}

/no_think"""

    return system_prompt, user_prompt


def _build_batch_classification_prompts(jobs: list[tuple[str, str]]) -> tuple[str, str]:
    """Build prompts that classify multiple jobs in one model request."""
    system_prompt = """You classify job postings into exactly one allowed category slug.
Rules:
- Treat each job independently
- Prefer the title and responsibilities over company industry
- Classify the job function, not its industry or workplace. Labels such as retail,
  automotive, sports, agriculture, or people operations are not allowed slugs; map
  them to the nearest job-function category instead.
- Ignore benefits, EEO/legal text, compensation boilerplate, location, and company marketing
- Return JSON only: [{"id":"0","category":"<allowed_slug>"}]
- Every input id must appear exactly once
- category must be one slug from the allowed list
- Never invent or transform a new slug
- If uncertain, choose the nearest allowed slug"""

    payload = [
        {
            "id": str(index),
            "title": title,
            "description": _truncate_description(description or ""),
        }
        for index, (title, description) in enumerate(jobs)
    ]
    user_prompt = f"""Allowed categories:
{_build_category_cards()}

Jobs JSON:
{json.dumps(payload, ensure_ascii=True, separators=(",", ":"))}

Return JSON only, one object per input id.

/no_think"""
    return system_prompt, user_prompt
