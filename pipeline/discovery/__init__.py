"""Browser discovery module for finding companies via Google search."""

from .browser_discovery import (
    discover_with_browser,
    save_discovered_companies,
    extract_company_slug,
    DiscoveryBrowser,
    main,
)

__all__ = [
    "discover_with_browser",
    "save_discovered_companies",
    "extract_company_slug",
    "DiscoveryBrowser",
    "main",
]
