"""Cleanup module for location normalization.

This module provides functionality for normalizing job location data,
including parsing location strings, normalizing state names, and batch
processing updates to the database.

Example:
    >>> from pipeline.stages.cleanup import cleanup_locations
    >>> await cleanup_locations(process_all=True)
    1500
"""

from pipeline.stages.cleanup.batch_updater import (
    cleanup_locations,
    delete_inactive_jobs,
)
from pipeline.stages.cleanup.location.cache import close_location_cache

__all__ = ["cleanup_locations", "close_location_cache", "delete_inactive_jobs"]
