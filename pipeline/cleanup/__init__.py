"""Cleanup module for location normalization.

This module provides functionality for normalizing job location data,
including parsing location strings, normalizing state names, and batch
processing updates to the database.

Example:
    >>> from pipeline.cleanup import cleanup_locations
    >>> await cleanup_locations(process_all=True)
    1500
"""

from pipeline.cleanup.batch_processor import (
    cleanup_locations,
    delete_inactive_jobs,
)

__all__ = ["cleanup_locations", "delete_inactive_jobs"]
