"""External job-source adapters and registries."""

from pipeline.sources.ashby import AshbyClient
from pipeline.sources.greenhouse import GreenhouseClient
from pipeline.sources.lever import LeverClient
from pipeline.sources.registry import get_all_slugs_by_ats, get_ashby_slugs, get_greenhouse_slugs, get_lever_slugs

__all__ = [
    "AshbyClient",
    "GreenhouseClient",
    "LeverClient",
    "get_all_slugs_by_ats",
    "get_ashby_slugs",
    "get_greenhouse_slugs",
    "get_lever_slugs",
]
