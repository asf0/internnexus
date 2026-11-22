"""Stable job identity helpers."""

from __future__ import annotations

import uuid


def fingerprint_for(apply_url: str) -> str:
    """Generate a stable fingerprint from a job's apply URL.

    Uses UUID5 with the URL namespace for deterministic, collision-resistant
    fingerprints that can be generated independently by both the pipeline
    and admin create paths.
    """
    normalized = apply_url.strip()
    if not normalized:
        raise ValueError("apply_url must not be empty")
    return str(uuid.uuid5(uuid.NAMESPACE_URL, normalized))
