"""Persistent slug-404 cooldown cache and partitioning.

A first 404 puts a slug into a transient cooldown (positive expiry) so a
temporary board outage cannot immediately retire it; a confirmed second 404
uses a negative marker that keeps it retired. Expired entries are pruned and
capped per source before the cache is written back atomically.
"""

from __future__ import annotations

import json
import logging
import os
import time

from pipeline.infra.paths import OUTPUT_DIR

logger = logging.getLogger(__name__)

SLUG_404_MAX_ENTRIES_PER_SOURCE = 500
SLUG_404_CACHE_PATH = OUTPUT_DIR / "slug_404_cache.json"


def load_slug_404_cache() -> dict[str, dict[str, float]]:
    """Load slug -> expiry timestamp cache for 404 cooldown suppression."""
    if not SLUG_404_CACHE_PATH.exists():
        return {}
    try:
        with open(SLUG_404_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        normalized: dict[str, dict[str, float]] = {}
        for source, source_map in data.items():
            if not isinstance(source_map, dict):
                continue
            normalized[source] = {}
            for slug, expires_at in source_map.items():
                try:
                    normalized[source][slug] = float(expires_at)
                except (TypeError, ValueError):
                    continue
        return normalized
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        logger.debug("Failed to load slug 404 cache: %s", exc)
        return {}


def prune_slug_404_cache(
    cache: dict[str, dict[str, float]],
    max_entries: int = SLUG_404_MAX_ENTRIES_PER_SOURCE,
) -> dict[str, dict[str, float]]:
    """Remove expired entries and cap per-source entry count.

    Keeps the most-recently expiring entries when a source exceeds the cap.
    """
    now_ts = time.time()
    pruned: dict[str, dict[str, float]] = {}
    for source, entries in cache.items():
        active = {slug: expires_at for slug, expires_at in entries.items() if abs(expires_at) > now_ts}
        if not active:
            continue
        if len(active) > max_entries:
            sorted_active = sorted(active.items(), key=lambda item: abs(item[1]), reverse=True)
            active = dict(sorted_active[:max_entries])
        pruned[source] = active
    return pruned


def save_slug_404_cache(cache: dict[str, dict[str, float]]) -> None:
    """Persist 404 cooldown cache to disk atomically."""
    try:
        SLUG_404_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = SLUG_404_CACHE_PATH.parent / f"{SLUG_404_CACHE_PATH.name}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(cache, f)
        os.replace(tmp_path, SLUG_404_CACHE_PATH)
    except (OSError, TypeError) as exc:
        logger.debug("Failed to save slug 404 cache: %s", exc)


def partition_cooldown_slugs(
    slugs: list[str], source_cache: dict[str, float], now_ts: float
) -> tuple[list[str], list[str], int]:
    """Split slugs into fetchable and retired, counting transient 404 cooldowns."""
    active_slugs: list[str] = []
    retired_slugs: list[str] = []
    transient_suppressed_count = 0

    for slug in slugs:
        marker = source_cache.get(slug)
        if marker and abs(marker) > now_ts:
            if marker > 0:
                transient_suppressed_count += 1
            else:
                retired_slugs.append(slug)
            continue
        active_slugs.append(slug)
    return active_slugs, retired_slugs, transient_suppressed_count
