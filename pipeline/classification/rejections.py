"""Rejection logging and unmapped-category curation for classification."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pipeline.classification.mapping import INVALID_CATEGORIES
from pipeline.classification.parser import (
    CANDIDATE_TOKEN_PATTERN,
    _normalize_slug_token,
)

MAX_REJECTION_SAMPLES_PER_BATCH = 5
REJECTION_LOG_RETENTION_DAYS = 7
LOW_SIGNAL_REJECTION_TOKENS = {
    "a",
    "an",
    "and",
    "category",
    "job",
    "m",
    "n_a",
    "na",
    "none",
    "null",
    "or",
    "other",
    "test",
    "the",
    "unknown",
}


def _is_high_signal_unmapped_candidate(category: str) -> bool:
    """Return True when a rejected candidate is useful for curation."""
    if not category:
        return False
    if category in LOW_SIGNAL_REJECTION_TOKENS:
        return False
    if category in INVALID_CATEGORIES:
        return False
    if category.isdigit() or len(category) < 3:
        return False
    return True


def _extract_rejection_slug_candidates(raw_output: str) -> set[str]:
    """Extract likely slug candidates from rejected model output."""
    candidates: set[str] = set()
    for raw_token in CANDIDATE_TOKEN_PATTERN.findall(raw_output):
        normalized = _normalize_slug_token(raw_token)
        if not normalized:
            continue
        if "_" not in normalized and len(normalized) < 4:
            continue
        if not _is_high_signal_unmapped_candidate(normalized):
            continue
        candidates.add(normalized)
    return candidates


def _write_unmapped_categories(candidates: set[str]) -> int:
    """Merge rejected slug candidates into unmapped_categories.json.

    Returns the number of newly-added slugs.
    """
    if not candidates:
        return 0

    log_path = Path(os.getenv("DATA_DIR", "data")) / "unmapped_categories.json"
    existing: set[str] = set()
    if log_path.exists():
        try:
            existing = set(json.loads(log_path.read_text()))
        except json.JSONDecodeError:
            existing = set()

    before = len(existing)
    existing.update(candidates)
    added = len(existing) - before
    if added:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps(sorted(existing), indent=2) + "\n")
    return added


def _get_rejection_log_path() -> Path:
    """Return today's date-stamped rejection log path."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return Path(os.getenv("DATA_DIR", "data")) / f"classification_rejections_{today}.jsonl"


def _rotate_rejection_logs() -> None:
    """Delete classification rejection logs older than retention window."""
    try:
        log_dir = Path(os.getenv("DATA_DIR", "data"))
        cutoff = datetime.now(timezone.utc) - timedelta(days=REJECTION_LOG_RETENTION_DAYS)
        for log_file in log_dir.glob("classification_rejections_*.jsonl"):
            try:
                date_str = log_file.stem.split("_")[-1]
                file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if file_date < cutoff:
                    log_file.unlink()
            except (ValueError, OSError):
                pass
    except OSError:
        pass


def _append_rejection_events(events: list[dict[str, str]]) -> None:
    """Append non-tokenizable classification rejections for review."""
    if not events:
        return

    _rotate_rejection_logs()
    log_path = _get_rejection_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(event, ensure_ascii=True) + "\n")
