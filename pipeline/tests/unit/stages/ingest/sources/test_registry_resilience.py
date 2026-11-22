"""Graceful handling of corrupt or missing data files."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from pipeline.stages.ingest.sources import registry as registry_module



@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    return tmp_path


def test_load_roster_missing_file_returns_defaults(
    temp_dir: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(registry_module, "ROSTER_FILE", temp_dir / "missing.json")
    assert registry_module.load_roster() == {"greenhouse": [], "lever": [], "ashby": []}


def test_load_roster_corrupt_json_returns_defaults(
    temp_dir: Path,
    monkeypatch,
) -> None:
    corrupt = temp_dir / "discovered_companies.json"
    corrupt.write_text("not json", encoding="utf-8")
    monkeypatch.setattr(registry_module, "ROSTER_FILE", corrupt)
    assert registry_module.load_roster() == {"greenhouse": [], "lever": [], "ashby": []}


def test_load_common_companies_missing_file_returns_empty(
    temp_dir: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(registry_module, "COMMON_COMPANIES_FILE", temp_dir / "missing.json")
    assert registry_module.load_common_companies() == []


def test_load_common_companies_corrupt_json_returns_empty(
    temp_dir: Path,
    monkeypatch,
) -> None:
    corrupt = temp_dir / "companies.json"
    corrupt.write_text("not json", encoding="utf-8")
    monkeypatch.setattr(registry_module, "COMMON_COMPANIES_FILE", corrupt)
    assert registry_module.load_common_companies() == []
