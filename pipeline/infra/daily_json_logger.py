"""Best-effort date-stamped JSONL persistence with retention."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DirectoryProvider = Path | Callable[[], Path]


class DailyJsonLogger:
    """Append JSON records to a daily file and rotate expired files."""

    def __init__(
        self,
        directory: DirectoryProvider,
        prefix: str,
        retention_days: int = 7,
        *,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        if retention_days < 0:
            raise ValueError("retention_days must be non-negative")
        self._directory = directory
        self._prefix = prefix
        self._retention_days = retention_days
        self._on_error = on_error
        self._last_rotation_check: date | None = None

    @property
    def directory(self) -> Path:
        """Resolve the output directory for the current operation."""
        if callable(self._directory):
            return self._directory()
        return self._directory

    def path_for(self, day: date | None = None) -> Path:
        """Return the JSONL path for a UTC calendar day."""
        resolved_day = day or datetime.now(timezone.utc).date()
        return self.directory / f"{self._prefix}_{resolved_day.isoformat()}.jsonl"

    def log(self, record: dict[str, Any]) -> None:
        """Append one JSON record."""
        self.log_many([record])

    def log_many(self, records: list[dict[str, Any]]) -> None:
        """Append records using one rotation check and one file open."""
        if not records:
            return
        try:
            self.rotate()
            path = self.path_for()
            path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
            os.chmod(path, 0o600)
            with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
                handle.writelines(json.dumps(record, ensure_ascii=True) + "\n" for record in records)
        except (OSError, TypeError) as exc:
            self._report_error(exc)

    def rotate(self, *, force: bool = False) -> None:
        """Delete files with dates older than the retention window."""
        today = datetime.now(timezone.utc).date()
        if not force and self._last_rotation_check == today:
            return
        self._last_rotation_check = today
        self._rotate_files(today)

    def _rotate_files(self, today: date) -> None:
        try:
            cutoff = today - timedelta(days=self._retention_days)
            for log_file in self.directory.glob(f"{self._prefix}_*.jsonl"):
                try:
                    date_text = log_file.stem.removeprefix(f"{self._prefix}_")
                    if date.fromisoformat(date_text) < cutoff:
                        log_file.unlink()
                except (OSError, ValueError):
                    continue
        except OSError as exc:
            self._report_error(exc)

    def _report_error(self, exc: Exception) -> None:
        if self._on_error is not None:
            self._on_error(exc)
