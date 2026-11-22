"""Company registry used by ingestion."""

from __future__ import annotations

import json
import logging
from pipeline.infra.paths import PACKAGE_DATA_DIR, company_roster_dir

logger = logging.getLogger(__name__)

#: Curated per-ATS slug roster, maintained by hand and mounted from a
#: persistent volume in deployments. The path and filename are historical --
#: this file was originally produced by a company-discovery step that has since
#: been retired -- and are deliberately unchanged so existing deployments keep
#: resolving it. It is the *only* source of Ashby slugs beyond the small
#: hardcoded ASHBY_KNOWN_SLUGS list, so losing it silently shrinks ingestion.
ROSTER_FILE = company_roster_dir() / "discovered_companies.json"
COMMON_COMPANIES_FILE = PACKAGE_DATA_DIR / "companies.json"


def load_roster() -> dict[str, list[str]]:
    """Load the curated per-ATS company slug roster.

    Returns:
        Dict mapping ATS platform names to lists of company slugs.
    """
    if ROSTER_FILE.exists():
        try:
            with open(ROSTER_FILE) as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except (OSError, json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"Could not load company roster: {e}")
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
    discovered = load_roster().get("greenhouse", [])
    common = load_common_companies()
    return sorted(set(discovered + common))


def get_lever_slugs() -> list[str]:
    """Get Lever slugs."""
    discovered = load_roster().get("lever", [])
    common = load_common_companies()
    return sorted(set(discovered + common))


def get_ashby_slugs() -> list[str]:
    """Get Ashby slugs.

    Generic company names produce many false 404s on Ashby because Ashby board
    slugs are usually discovered-specific and do not match public company names.
    """
    discovered = load_roster().get("ashby", [])
    try:
        from pipeline.stages.ingest.sources.ashby import ASHBY_KNOWN_SLUGS
    except ImportError as exc:
        logger.warning("Could not load known Ashby slugs: %s", exc)
        known = []
    else:
        known = ASHBY_KNOWN_SLUGS
    return sorted(set(discovered + known))
