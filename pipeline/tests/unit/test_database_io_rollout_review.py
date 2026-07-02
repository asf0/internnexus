"""Regression tests for the production rollout evidence reviewer."""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
REVIEWER_PATH = REPOSITORY_ROOT / "tools" / "database_io" / "review-db-io-rollout.py"
pytestmark = pytest.mark.skipif(
    not REVIEWER_PATH.exists(),
    reason="Local database I/O rollout reviewer is not tracked",
)


def _load_reviewer():
    spec = importlib.util.spec_from_file_location("database_io_rollout_review", REVIEWER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_snapshot(
    root: Path,
    captured_at: datetime,
    *,
    backend_ok: bool = True,
    checkpoint_warning: bool = False,
    pipeline_failure: bool = False,
    root_usage: int = 49,
    source_complete: bool = True,
) -> None:
    snapshot = root / captured_at.strftime("%Y%m%dT%H%M%SZ")
    snapshot.mkdir()
    (snapshot / "captured-at.txt").write_text(captured_at.isoformat().replace("+00:00", "Z"))
    (snapshot / "backend-health.status").write_text("ok" if backend_ok else "failed")
    service_records = [
        {
            "name": name,
            "image": "sha256:test",
            "started_at": captured_at.isoformat(),
            "status": "running",
            "health": "healthy",
        }
        for name in ("/jobs-db", "/jobs-backend", "/jobs-pipeline")
    ]
    (snapshot / "service-states.jsonl").write_text("".join(json.dumps(record) + "\n" for record in service_records))
    checkpoint_log = "checkpoints are occurring too frequently" if checkpoint_warning else ""
    (snapshot / "checkpoint-logs.txt").write_text(checkpoint_log)
    (snapshot / "pipeline-log-summary.txt").write_text("Pipeline failed" if pipeline_failure else "PIPELINE COMPLETE")
    (snapshot / "filesystem.txt").write_text(
        f"Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/test 100 49 51 {root_usage}% /\n"
    )
    results = {
        "jobs_fetched": 278_000,
        "jobs_changed": 300,
        "source_complete": {
            "greenhouse": source_complete,
            "lever": source_complete,
            "ashby": source_complete,
        },
        "sync_skipped_reasons": [] if source_complete else ["incomplete sources"],
    }
    (snapshot / "postgres.json").write_text(
        json.dumps(
            {
                "latest_pipeline_run": {
                    "id": "run-safe",
                    "status": "completed",
                    "results": results,
                }
            }
        )
    )


def test_review_passes_complete_healthy_24_hour_window(tmp_path: Path) -> None:
    reviewer = _load_reviewer()
    started = datetime(2026, 6, 30, 16, 0, tzinfo=timezone.utc)
    _write_snapshot(tmp_path, started)
    _write_snapshot(tmp_path, started + timedelta(hours=24, minutes=30))

    assert reviewer.review(tmp_path, minimum_hours=24) == []


def test_review_rejects_short_window(tmp_path: Path) -> None:
    reviewer = _load_reviewer()
    started = datetime(2026, 6, 30, 16, 0, tzinfo=timezone.utc)
    _write_snapshot(tmp_path, started)
    _write_snapshot(tmp_path, started + timedelta(hours=4))

    failures = reviewer.review(tmp_path, minimum_hours=24)

    assert any("minimum is 24.00h" in failure for failure in failures)


def test_review_rejects_operational_and_safety_failures(tmp_path: Path) -> None:
    reviewer = _load_reviewer()
    started = datetime(2026, 6, 30, 16, 0, tzinfo=timezone.utc)
    _write_snapshot(tmp_path, started)
    _write_snapshot(
        tmp_path,
        started + timedelta(hours=25),
        backend_ok=False,
        checkpoint_warning=True,
        pipeline_failure=True,
        root_usage=80,
        source_complete=False,
    )

    failures = reviewer.review(tmp_path, minimum_hours=24)

    assert any("backend health failed" in failure for failure in failures)
    assert any("frequent checkpoint warning" in failure for failure in failures)
    assert any("pipeline failure" in failure for failure in failures)
    assert any("root filesystem usage is 80%" in failure for failure in failures)
