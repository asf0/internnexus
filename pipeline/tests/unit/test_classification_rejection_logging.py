from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.classification import JobClassifier
from pipeline.classification.mapping import _log_unmapped_category
from pipeline.classification.service import (
    _get_rejection_log_path,
    _rotate_rejection_logs,
)
from pipeline.classification.rejections import (
    _append_rejection_events,
    _write_unmapped_categories,
)


def _rejection_log_path(data_dir: Path) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return data_dir / f"classification_rejections_{today}.jsonl"


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

    events_path = _rejection_log_path(tmp_path)
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
    assert _rejection_log_path(tmp_path).exists()


def test_get_rejection_log_path_uses_daily_suffix(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    expected = _rejection_log_path(tmp_path)
    assert _get_rejection_log_path() == expected


def test_rejection_log_rotation_deletes_old_files(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    old_date = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")
    old_log = tmp_path / f"classification_rejections_{old_date}.jsonl"
    old_log.write_text("{}")

    _rotate_rejection_logs()

    assert not old_log.exists()


def test_rejection_log_rotation_keeps_recent_files(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    recent_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    recent_log = tmp_path / f"classification_rejections_{recent_date}.jsonl"
    recent_log.write_text("{}")

    _rotate_rejection_logs()

    assert recent_log.exists()


def _make_read_only(tmp_path: Path) -> Path:
    """Return a read-only DATA_DIR equivalent that still allows reading."""
    read_only_dir = tmp_path / "readonly"
    read_only_dir.mkdir(parents=True, exist_ok=True)
    # Remove write permission for owner/group/others.
    read_only_dir.chmod(0o555)
    return read_only_dir


def test_write_unmapped_categories_is_resilient_to_permission_errors(
    tmp_path, monkeypatch, caplog
):
    read_only_dir = _make_read_only(tmp_path)
    monkeypatch.setenv("DATA_DIR", str(read_only_dir))

    with caplog.at_level("WARNING"):
        added = _write_unmapped_categories({"some_new_category"})

    assert added == 0
    assert "Failed to write unmapped categories" in caplog.text
    assert "Permission denied" in caplog.text or "Permission" in caplog.text


def test_append_rejection_events_is_resilient_to_permission_errors(
    tmp_path, monkeypatch, caplog
):
    read_only_dir = _make_read_only(tmp_path)
    monkeypatch.setenv("DATA_DIR", str(read_only_dir))

    with caplog.at_level("WARNING"):
        _append_rejection_events(
            [{"reason": "empty_response", "title": "Role", "raw_output": ""}]
        )

    assert "Failed to write classification rejection events" in caplog.text
    assert "Permission denied" in caplog.text or "Permission" in caplog.text


def test_log_unmapped_category_is_resilient_to_permission_errors(
    tmp_path, monkeypatch, caplog
):
    read_only_dir = _make_read_only(tmp_path)
    monkeypatch.setenv("DATA_DIR", str(read_only_dir))

    with caplog.at_level("WARNING"):
        _log_unmapped_category("unmapped_category")

    assert "Failed to write unmapped category" in caplog.text
    assert "Permission denied" in caplog.text or "Permission" in caplog.text
