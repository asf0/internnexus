"""Tests for shared daily JSONL logging."""

from __future__ import annotations

import json
import stat
from datetime import datetime, timedelta, timezone

from pipeline.infra.daily_json_logger import DailyJsonLogger


def test_log_and_log_many_append_one_record_per_line(tmp_path) -> None:
    logger = DailyJsonLogger(tmp_path, "events")

    logger.log({"id": 1})
    logger.log_many([{"id": 2}, {"id": 3}])

    records = [json.loads(line) for line in logger.path_for().read_text().splitlines()]
    assert records == [{"id": 1}, {"id": 2}, {"id": 3}]


def test_rotate_deletes_only_expired_matching_files(tmp_path) -> None:
    logger = DailyJsonLogger(tmp_path, "events", retention_days=7)
    old_day = (datetime.now(timezone.utc) - timedelta(days=8)).date()
    recent_day = (datetime.now(timezone.utc) - timedelta(days=2)).date()
    old_path = logger.path_for(old_day)
    recent_path = logger.path_for(recent_day)
    unrelated_path = tmp_path / f"other_{old_day.isoformat()}.jsonl"
    for path in (old_path, recent_path, unrelated_path):
        path.write_text("{}\n")

    logger.rotate()

    assert not old_path.exists()
    assert recent_path.exists()
    assert unrelated_path.exists()


def test_log_errors_are_reported_without_raising(tmp_path) -> None:
    errors: list[Exception] = []
    logger = DailyJsonLogger(tmp_path, "events", on_error=errors.append)

    logger.log({"not_serializable": object()})

    assert len(errors) == 1
    assert isinstance(errors[0], TypeError)


def test_rotation_scan_runs_at_most_once_per_day(tmp_path, monkeypatch) -> None:
    logger = DailyJsonLogger(tmp_path, "events")
    scans: list[object] = []
    monkeypatch.setattr(logger, "_rotate_files", scans.append)

    logger.log({"id": 1})
    logger.log({"id": 2})

    assert len(scans) == 1


def test_log_files_are_owner_only(tmp_path) -> None:
    logger = DailyJsonLogger(tmp_path, "events")
    logger.log({"id": 1})

    assert stat.S_IMODE(logger.path_for().stat().st_mode) == 0o600
