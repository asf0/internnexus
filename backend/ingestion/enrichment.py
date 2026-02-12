from __future__ import annotations

import logging
import re

from app.services.embedding_service import EmbeddingService
#from app.services.visa_classifier import VisaClassifier
from ingestion.data.constants import US_STATES
from ingestion.schemas import JobSchema


logger = logging.getLogger(__name__)


# Country abbreviations to full names
COUNTRIES = {
    "USA": "United States",
    "US": "United States",
    "UK": "United Kingdom",
    "GB": "United Kingdom",
    "CA": "Canada",
    "AU": "Australia",
    "NZ": "New Zealand",
    "DE": "Germany",
    "FR": "France",
    "ES": "Spain",
    "IT": "Italy",
    "JP": "Japan",
    "CN": "China",
    "IN": "India",
    "BR": "Brazil",
    "MX": "Mexico",
    "SG": "Singapore",
    "HK": "Hong Kong",
    "NL": "Netherlands",
    "BE": "Belgium",
    "CH": "Switzerland",
    "SE": "Sweden",
    "NO": "Norway",
    "DK": "Denmark",
    "FI": "Finland",
    "PL": "Poland",
    "CZ": "Czech Republic",
    "IE": "Ireland",
}


def normalize_location(location: str) -> dict:
    """Normalize location and return dict with city, state, country as separate fields.

    Returns:
        dict with keys 'full' (combined string), 'city', 'state', 'country'
    """
    if not location or not location.strip():
        return {"full": None, "city": None, "state": None, "country": None}

    location = location.strip()

    # Skip if it looks like a full street address (starts with number AND contains address keywords)
    location_lower = location.lower()
    if re.match(r"^\d+", location) and any(
        keyword in location_lower
        for keyword in [
            "street",
            "avenue",
            "ave",
            "st",
            "rd",
            "dr",
            "ln",
            "blvd",
            "pkwy",
            "plaza",
            "road",
        ]
    ):
        return {"full": None, "city": None, "state": None, "country": None}

    # Remove parentheses and content inside
    location = re.sub(r"\([^)]*\)", "", location).strip()

    # Skip placeholder/generic locations
    skip_patterns = [
        "add location here",
        "amer",
        "amer - us",
        "tbd",
        "varies",
        "multiple",
        "unknown",
        "any",
        "any location",
    ]
    if location.lower() in skip_patterns or any(x in location.lower() for x in skip_patterns):
        return {"full": None, "city": None, "state": None, "country": None}

    # Handle remote/flexible locations
    if any(x in location.lower() for x in ["remote", "flexible", "anywhere"]):
        return {"full": "Remote", "city": None, "state": None, "country": None}

    # Clean up weird characters
    location = re.sub(r"[/\\|]+", " ", location)
    location = re.sub(r"\s*-\s*", ", ", location)

    # Extract the first location from semicolon-separated lists (only semicolon, not comma yet)
    if ";" in location:
        location = location.split(";")[0].strip()

    location = location.strip()

    # Skip very long locations (likely multi-location listings)
    if len(location) > 100:
        return {"full": None, "city": None, "state": None, "country": None}

    # Skip if too short
    if len(location) < 2:
        return {"full": None, "city": None, "state": None, "country": None}

    # Normalize spaces
    location = re.sub(r"\s+", " ", location).strip()

    # Now split by comma for city, state, country parts
    parts = [p.strip() for p in location.split(",")]

    # If we have space-separated parts without commas, treat space-separated as well
    # E.g., "Boston MA" -> ["Boston", "MA"]
    if len(parts) == 1 and " " in parts[0]:
        space_parts = parts[0].split()
        # If last part is 2 letters, it might be state abbreviation
        if len(space_parts) >= 2 and len(space_parts[-1]) == 2:
            last_part_upper = space_parts[-1].upper()
            if last_part_upper in US_STATES:
                parts = [" ".join(space_parts[:-1]), space_parts[-1]]

    # Process each part and expand abbreviations with smart context awareness
    expanded_parts = []

    # Check if the last part looks like a country code (but not a state abbreviation)
    last_part = parts[-1].upper() if parts else ""
    has_country_at_end = (
        last_part and len(last_part) <= 3 and last_part in COUNTRIES and last_part not in US_STATES
    )  # Exclude if it's also a state

    for i, part in enumerate(parts):
        if not part:
            continue

        part_upper = part.upper()

        # For 2-letter codes, use context to determine if state or country
        if len(part_upper) == 2:
            # Position-based logic:
            # - If we already have a country at the end, treat middle 2-letter codes as states
            # - Middle position (not first, not last): likely state if has_country_at_end
            # - Last position: prefer state unless it's a known country code without a state match
            is_middle = i > 0 and i < len(parts) - 1
            is_last = i == len(parts) - 1

            if is_middle and has_country_at_end:
                # Middle position with country at end -> must be state
                if part_upper in US_STATES:
                    expanded_parts.append(US_STATES[part_upper])
                elif part_upper in COUNTRIES:
                    expanded_parts.append(COUNTRIES[part_upper])
                else:
                    expanded_parts.append(part.title())
            elif is_last and not has_country_at_end:
                # Last position without country -> likely a state (most common in US)
                # Only treat as country if it's NOT a state
                if part_upper in US_STATES:
                    expanded_parts.append(US_STATES[part_upper])
                elif part_upper in COUNTRIES:
                    expanded_parts.append(COUNTRIES[part_upper])
                else:
                    expanded_parts.append(part.title())
            elif is_last and has_country_at_end:
                # Last position with country already present -> this is the country
                if part_upper in COUNTRIES:
                    expanded_parts.append(COUNTRIES[part_upper])
                elif part_upper in US_STATES:
                    expanded_parts.append(US_STATES[part_upper])
                else:
                    expanded_parts.append(part.title())
            else:
                # First position or default: prefer state for US context
                if part_upper in US_STATES:
                    expanded_parts.append(US_STATES[part_upper])
                elif part_upper in COUNTRIES:
                    expanded_parts.append(COUNTRIES[part_upper])
                else:
                    expanded_parts.append(part.title())
        elif part_upper in COUNTRIES:
            expanded_parts.append(COUNTRIES[part_upper])
        else:
            # Keep as-is with proper capitalization
            expanded_parts.append(part.title())

    # Rejoin with comma-space
    full_location = ", ".join(expanded_parts)

    # Parse into city, state, country based on position
    city = None
    state = None
    country = None

    if expanded_parts:
        if len(expanded_parts) == 1:
            # Single part: treat as city
            city = expanded_parts[0]
        elif len(expanded_parts) == 2:
            # Two parts: could be city, state OR city, country
            # Check if second part is a country (expanded)
            if any(expanded_parts[1] == v for v in COUNTRIES.values()):
                city = expanded_parts[0]
                country = expanded_parts[1]
            else:
                # Otherwise treat as city, state
                city = expanded_parts[0]
                state = expanded_parts[1]
        else:
            # Three or more parts: city, state, country
            city = expanded_parts[0]
            # Last part is usually country if it's a full country name
            if any(expanded_parts[-1] == v for v in COUNTRIES.values()):
                country = expanded_parts[-1]
                state = expanded_parts[1] if len(expanded_parts) > 2 else None
            else:
                # Otherwise middle is state, last is country
                state = expanded_parts[1] if len(expanded_parts) > 1 else None
                country = expanded_parts[2] if len(expanded_parts) > 2 else None

    return {
        "full": full_location if full_location else None,
        "city": city,
        "state": state,
        "country": country,
    }


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

    # Initialize classifier (may be None if no API keys available)
    # try:
    #     classifier = VisaClassifier()
    # except RuntimeError:
    #     classifier = None

    # Initialize embedder only if we're not skipping
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
