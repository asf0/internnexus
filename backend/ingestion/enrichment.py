from __future__ import annotations

import logging
import re

from app.services.embedding_service import EmbeddingService
from ingestion.data.constants import US_STATES
from ingestion.schemas import JobSchema
from ingestion.location_normalizer import normalize_location


logger = logging.getLogger(__name__)


class LegendAttributeDetector:
    """Detect legend attributes from job descriptions and metadata."""

    def detect_requires_sponsorship(self, description: str, title: str) -> bool:
        """Detect if job does NOT offer sponsorship (🛂 marker)."""
        if not description:
            return False
        # Look for common "no sponsorship" patterns
        patterns = [
            r"does\s+not\s+offer\s+sponsorship",
            r"no\s+sponsorship",
            r"sponsorship\s+not\s+available",
            r"cannot\s+sponsor",
        ]
        return any(re.search(pattern, description, re.IGNORECASE) for pattern in patterns)

    def detect_requires_us_citizenship(self, description: str, title: str) -> bool:
        """Detect if job requires U.S. Citizenship (🇺🇸 marker)."""
        if not description:
            return False
        patterns = [
            r"u\.?s\.?\s+citizen",
            r"us\s+citizen",
            r"united\s+states\s+citizen",
            r"citizenship\s+required",
        ]
        return any(re.search(pattern, description, re.IGNORECASE) for pattern in patterns)

    def detect_application_closed(self, description: str, title: str) -> bool:
        """Detect if application is closed (🔒 marker)."""
        if not description:
            return False
        patterns = [
            r"application\s+closed",
            r"application\s+is\s+closed",
            r"no\s+longer\s+accepting",
            r"not\s+currently\s+accepting",
        ]
        return any(re.search(pattern, description, re.IGNORECASE) for pattern in patterns)

    def detect_is_faang_plus(self, company: str) -> bool:
        """Detect if company is FAANG+ (🔥 marker)."""
        faang_companies = {
            "facebook",
            "meta",
            "amazon",
            "apple",
            "netflix",
            "google",
            "microsoft",
            "tesla",
            "nvidia",
            "stripe",
            "databricks",
            "figma",
            "discord",
            "airbnb",
            "dropbox",
            "twilio",
            "okta",
            "plaid",
            "cloudflare",
            "coinbase",
            "roblox",
        }
        return company.lower() in faang_companies

    def detect_requires_advanced_degree(self, description: str, title: str) -> bool:
        """Detect if advanced degree is required (🎓 marker)."""
        if not description:
            return False
        patterns = [
            r"master[\'s]*\s+degree\s+required",
            r"phd\s+required",
            r"mba\s+required",
            r"graduate\s+degree\s+required",
            r"advanced\s+degree\s+required",
            r"master[\'s]*\s+student",
            r"phd\s+student",
            r"graduate\s+student",
        ]
        return any(re.search(pattern, description, re.IGNORECASE) for pattern in patterns)


class CategoryDetector:
    """Detect job category from title and description."""

    def detect_category(self, title: str, description: str) -> str | None:
        """Detect job category based on title and description."""
        title_lower = title.lower()
        description_lower = description.lower() if description else ""

        # Software Engineering patterns
        if any(
            word in title_lower
            for word in [
                "software",
                "engineer",
                "developer",
                "programmer",
                "backend",
                "frontend",
                "fullstack",
                "swe",
            ]
        ):
            return "software_engineering"

        # Product Management patterns
        if (
            any(word in title_lower for word in ["product", "pm", "manager"])
            and "product engineer" not in title_lower
        ):
            return "product_management"

        # Data Science & AI patterns
        if any(
            word in title_lower
            for word in [
                "data",
                "machine learning",
                "ml",
                "ai",
                "artificial intelligence",
                "data science",
                "analytics",
                "data analyst",
            ]
        ):
            return "data_science_ai"

        # Quantitative Finance patterns
        if any(
            word in title_lower
            for word in ["quant", "trading", "finance", "financial", "risk analysis", "derivatives"]
        ):
            return "quantitative_finance"

        # Hardware Engineering patterns
        if any(
            word in title_lower
            for word in [
                "hardware",
                "circuit",
                "embedded",
                "firmware",
                "electrical",
                "mechanical",
                "physical design",
            ]
        ):
            return "hardware_engineering"

        return None


async def enrich_jobs(
    jobs: list[JobSchema],
    category_context: dict[str, str] | None = None,
    skip_embedding: bool = False,
) -> list[JobSchema]:
    """Enrich jobs with visa info, categories, and other attributes.

    Args:
        jobs: List of jobs to enrich
        category_context: Optional dict mapping job positions to categories from markdown parsing
        skip_embedding: If True, skip the embedding step (embeddings done separately after DB insert)
    """
    if not jobs:
        return []

    embedder = None
    if not skip_embedding:
        try:
            embedder = EmbeddingService()
        except RuntimeError:
            embedder = None

    legend_detector = LegendAttributeDetector()
    category_detector = CategoryDetector()

    category_context = category_context or {}

    for job in jobs:
        # Normalize location and parse into city/state/country
        location_data = normalize_location(job.location)
        job.location = (
            location_data.get("full") or job.location
        )  # Keep original if normalization failed
        job.city = location_data.get("city")
        job.state = location_data.get("state")
        job.country = location_data.get("country")

        if job.description_text:
            # Classify visa sponsorship (skip if no API keys available)
            # if classifier:
            #     visa = classifier.classify(job.description_text)
            #     job.visa_sponsored = visa.get("visa")
            #     job.f1_friendly = visa.get("f1")

            # Embed description (only if embedder is available and not skipped)
            if embedder:
                try:
                    job.description_embedding = await embedder.embed(job.description_text)
                except Exception as e:
                    logger.warning(f"Failed to embed job {job.title} at {job.company}: {e}")
                    job.description_embedding = None

            # Detect legend attributes
            job.requires_sponsorship = legend_detector.detect_requires_sponsorship(
                job.description_text, job.title
            )
            job.requires_us_citizenship = legend_detector.detect_requires_us_citizenship(
                job.description_text, job.title
            )
            job.application_closed = legend_detector.detect_application_closed(
                job.description_text, job.title
            )
            job.requires_advanced_degree = legend_detector.detect_requires_advanced_degree(
                job.description_text, job.title
            )

        # Detect FAANG+ by company
        job.is_faang_plus = legend_detector.detect_is_faang_plus(job.company)

        # Detect or use provided category
        if job.company in category_context:
            job.job_category = category_context[job.company]
        else:
            job.job_category = category_detector.detect_category(
                job.title, job.description_text or ""
            )

    return jobs
