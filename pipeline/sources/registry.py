"""Company registry used by ingestion."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_DISCOVERY_DIR = Path(__file__).parent.parent / "discovery" / "output"
DISCOVERY_FILE = Path(os.environ.get("DISCOVERY_OUTPUT_DIR", str(DEFAULT_DISCOVERY_DIR))) / "discovered_companies.json"
COMMON_COMPANIES_FILE = Path(__file__).parent.parent / "data" / "companies.json"


def load_discovery_results() -> dict[str, list[str]]:
    """Load companies from discovery output file.

    Returns:
        Dict mapping ATS platform names to lists of company slugs.
    """
    if DISCOVERY_FILE.exists():
        try:
            with open(DISCOVERY_FILE) as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except (OSError, json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"Could not load discovery results: {e}")
    return {"greenhouse": [], "lever": [], "ashby": []}


def load_common_companies() -> list[str]:
    """Load common company slugs (companies not in discovered)."""
    if COMMON_COMPANIES_FILE.exists():
        try:
            with open(COMMON_COMPANIES_FILE) as f:
                data = json.load(f)
                return data.get("common_slugs", [])
        except (OSError, json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"Could not load common companies: {e}")
    return []


def get_greenhouse_slugs() -> list[str]:
    """Get Greenhouse slugs."""
    discovered = load_discovery_results().get("greenhouse", [])
    common = load_common_companies()
    return sorted(set(discovered + common))


def get_lever_slugs() -> list[str]:
    """Get Lever slugs."""
    discovered = load_discovery_results().get("lever", [])
    common = load_common_companies()
    return sorted(set(discovered + common))


def get_ashby_slugs() -> list[str]:
    """Get Ashby slugs.

    Generic company names produce many false 404s on Ashby because Ashby board
    slugs are usually discovered-specific and do not match public company names.
    """
    discovered = load_discovery_results().get("ashby", [])
    try:
        from pipeline.sources.ashby import ASHBY_KNOWN_SLUGS
    except ImportError as exc:
        logger.warning("Could not load known Ashby slugs: %s", exc)
        known = []
    else:
        known = ASHBY_KNOWN_SLUGS
    return sorted(set(discovered + known))


def get_all_slugs_by_ats() -> dict[str, list[str]]:
    """Get all slugs grouped by ATS platform."""
    return {
        "greenhouse": get_greenhouse_slugs(),
        "lever": get_lever_slugs(),
        "ashby": get_ashby_slugs(),
    }
