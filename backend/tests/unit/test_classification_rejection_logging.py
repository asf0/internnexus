from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.classification import JobClassifier


@pytest.mark.asyncio
async def test_rejected_outputs_write_unmapped_candidates(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    async def _fake_classify(self, title: str, description: str):
        del self, title, description
        await asyncio.sleep(0)
        return None, "no_mappable_token", "vehicle_maintenance"

    monkeypatch.setattr(JobClassifier, "_classify_job_with_reason", _fake_classify)

    classifier = JobClassifier(model="dummy", base_url="http://localhost:11434", provider="ollama")
    results = await classifier.classify_batch_with_reasons([("Role A", "Desc"), ("Role B", "Desc")])

    assert results == [(None, "no_mappable_token"), (None, "no_mappable_token")]

    unmapped_path = tmp_path / "unmapped_categories.json"
    assert unmapped_path.exists()
    values = json.loads(unmapped_path.read_text())
    assert values == ["vehicle_maintenance"]


@pytest.mark.asyncio
async def test_rejected_outputs_without_tokens_write_jsonl_events(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    async def _fake_classify(self, title: str, description: str):
        del self, title, description
        await asyncio.sleep(0)
        return None, "empty_response", ""

    monkeypatch.setattr(JobClassifier, "_classify_job_with_reason", _fake_classify)

    classifier = JobClassifier(model="dummy", base_url="http://localhost:11434", provider="ollama")
    results = await classifier.classify_batch_with_reasons([("Role C", "Desc")])

    assert results == [(None, "empty_response")]

    events_path = tmp_path / "classification_rejections.jsonl"
    assert events_path.exists()
    lines = [line for line in events_path.read_text().splitlines() if line]
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["reason"] == "empty_response"
    assert payload["title"] == "Role C"


@pytest.mark.asyncio
async def test_low_signal_rejected_tokens_are_not_added_to_unmapped(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    async def _fake_classify(self, title: str, description: str):
        del self, title, description
        await asyncio.sleep(0)
        return None, "no_mappable_token", "test"

    monkeypatch.setattr(JobClassifier, "_classify_job_with_reason", _fake_classify)

    classifier = JobClassifier(model="dummy", base_url="http://localhost:11434", provider="ollama")
    results = await classifier.classify_batch_with_reasons([("Role D", "Desc")])

    assert results == [(None, "no_mappable_token")]
    assert not (tmp_path / "unmapped_categories.json").exists()
    assert (tmp_path / "classification_rejections.jsonl").exists()
