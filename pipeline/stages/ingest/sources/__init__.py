"""External job-source adapters and registries."""

from pipeline.stages.ingest.sources.ashby import AshbyClient
from pipeline.stages.ingest.sources.greenhouse import GreenhouseClient
from pipeline.stages.ingest.sources.lever import LeverClient
from pipeline.stages.ingest.sources.protocols import JobSourceClient
from pipeline.stages.ingest.sources.registry import get_ashby_slugs, get_greenhouse_slugs, get_lever_slugs

__all__ = [
    "AshbyClient",
    "GreenhouseClient",
    "JobSourceClient",
    "LeverClient",
    "get_ashby_slugs",
    "get_greenhouse_slugs",
    "get_lever_slugs",
]
