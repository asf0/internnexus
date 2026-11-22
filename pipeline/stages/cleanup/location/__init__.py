"""Location normalization public API.

Data vs. code:
Static lookup data lives in ``data/location_constants.json`` and is exposed
through ``constants.py``. Parsing behavior lives in the focused country,
state, city, and normalization submodules.
"""

from pipeline.stages.cleanup.location.normalize import normalize_location

__all__ = [
    "normalize_location",
]
