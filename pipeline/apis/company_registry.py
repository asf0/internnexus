"""Company registry - manages company slugs for job fetching."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

BROWSER_DISCOVERY_FILE = Path(__file__).parent.parent / "discovery" / "output" / "discovered_companies.json"
COMMON_COMPANIES_FILE = Path(__file__).parent.parent / "data" / "companies.json"


def load_browser_discovery_results() -> dict[str, list[str]]:
    """Load companies from browser discovery output file.

    Returns:
        Dict mapping ATS platform names to lists of company slugs.
    """
    if BROWSER_DISCOVERY_FILE.exists():
        try:
            with open(BROWSER_DISCOVERY_FILE) as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            logger.warning(f"Could not load browser discovery results: {e}")
    return {"greenhouse": [], "lever": [], "ashby": []}


def load_common_companies() -> list[str]:
    """Load common company slugs (companies not in discovered)."""
    if COMMON_COMPANIES_FILE.exists():
        try:
            with open(COMMON_COMPANIES_FILE) as f:
                data = json.load(f)
                return data.get("common_slugs", [])
        except Exception as e:
            logger.warning(f"Could not load common companies: {e}")
    return []


def get_greenhouse_slugs() -> list[str]:
    """Get GH slugs = GH-discovered + common (deduped)."""
    discovered = load_browser_discovery_results().get("greenhouse", [])
    common = load_common_companies()
    return list(set(discovered + common))


def get_lever_slugs() -> list[str]:
    """Get Lever slugs = Lever-discovered + common (deduped)."""
    discovered = load_browser_discovery_results().get("lever", [])
    common = load_common_companies()
    return list(set(discovered + common))


def get_ashby_slugs() -> list[str]:
    """Get Ashby slugs = Ashby-discovered + common (deduped)."""
    discovered = load_browser_discovery_results().get("ashby", [])
    common = load_common_companies()
    return list(set(discovered + common))


def get_all_slugs_by_ats() -> dict[str, list[str]]:
    """Get all slugs grouped by ATS platform."""
    return {
        "greenhouse": get_greenhouse_slugs(),
        "lever": get_lever_slugs(),
        "ashby": get_ashby_slugs(),
    }
