"""Graceful handling of corrupt or missing data files."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

import pipeline.stages.ingest.slug_cooldown as ingest_core
from pipeline.stages.ingest.slug_cooldown import (
    load_slug_404_cache as _load_slug_404_cache,
    prune_slug_404_cache as _prune_slug_404_cache,
    save_slug_404_cache as _save_slug_404_cache,
)
from pipeline.stages.ingest.sources import registry as registry_module



@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    return tmp_path


def test_load_slug_404_cache_missing_file_returns_empty(
    temp_dir: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(ingest_core, "SLUG_404_CACHE_PATH", temp_dir / "slug_404_cache.json")
    assert _load_slug_404_cache() == {}


def test_load_slug_404_cache_corrupt_json_returns_empty(
    temp_dir: Path,
    monkeypatch,
) -> None:
    corrupt = temp_dir / "slug_404_cache.json"
    corrupt.write_text("not json", encoding="utf-8")
    monkeypatch.setattr(ingest_core, "SLUG_404_CACHE_PATH", corrupt)
    assert _load_slug_404_cache() == {}


def test_load_slug_404_cache_invalid_values_are_ignored(
    temp_dir: Path,
    monkeypatch,
) -> None:
    cache_file = temp_dir / "slug_404_cache.json"
    cache_file.write_text(
        json.dumps({"greenhouse": {"valid": 12345.0, "invalid": "not-a-number"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(ingest_core, "SLUG_404_CACHE_PATH", cache_file)
    result = _load_slug_404_cache()
    assert "greenhouse" in result
    assert "valid" in result["greenhouse"]
    assert "invalid" not in result["greenhouse"]


def test_slug_cache_prune_removes_expired_entries() -> None:
    now = time.time()
    cache = {
        "greenhouse": {
            "active": now + 3600,
            "expired": now - 1,
        }
    }
    pruned = _prune_slug_404_cache(cache)
    assert "active" in pruned["greenhouse"]
    assert "expired" not in pruned["greenhouse"]


def test_slug_cache_prune_caps_per_source() -> None:
    now = time.time()
    cache = {"greenhouse": {f"slug_{i}": now + i for i in range(10)}}
    pruned = _prune_slug_404_cache(cache, max_entries=3)
    assert len(pruned["greenhouse"]) == 3
    # Most-recently expiring entries should be retained.
    assert set(pruned["greenhouse"]) == {"slug_7", "slug_8", "slug_9"}


def test_slug_cache_prune_drops_empty_sources() -> None:
    now = time.time()
    cache = {
        "greenhouse": {"expired": now - 1},
        "lever": {"active": now + 3600},
    }
    pruned = _prune_slug_404_cache(cache)
    assert "greenhouse" not in pruned
    assert "lever" in pruned


def test_slug_cache_atomic_write_saves_target_and_cleans_tmp(
    temp_dir: Path,
    monkeypatch,
) -> None:
    cache_file = temp_dir / "slug_404_cache.json"
    monkeypatch.setattr(ingest_core, "SLUG_404_CACHE_PATH", cache_file)
    cache = {"greenhouse": {"slug": 12345.0}}

    _save_slug_404_cache(cache)

    assert cache_file.exists()
    assert json.loads(cache_file.read_text()) == cache
    assert not (temp_dir / "slug_404_cache.json.tmp").exists()


def test_slug_cache_load_after_atomic_write_round_trips(
    temp_dir: Path,
    monkeypatch,
) -> None:
    cache_file = temp_dir / "slug_404_cache.json"
    monkeypatch.setattr(ingest_core, "SLUG_404_CACHE_PATH", cache_file)
    cache = {"greenhouse": {"slug": 12345.0}}

    _save_slug_404_cache(cache)
    loaded = _load_slug_404_cache()

    assert loaded == {"greenhouse": {"slug": 12345.0}}
