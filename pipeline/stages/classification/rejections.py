"""Rejection logging and unmapped-category curation for classification."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from pipeline.stages.classification.mapping import INVALID_CATEGORIES
from pipeline.stages.classification.response_parser import (
    CANDIDATE_TOKEN_PATTERN,
    _normalize_slug_token,
)
from pipeline.infra.daily_json_logger import DailyJsonLogger
from pipeline.infra.paths import runtime_data_dir

logger = logging.getLogger(__name__)

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


def _rejection_log_error(exc: Exception) -> None:
    logger.warning(
        "Failed to write classification rejection events to %s: %s",
        _get_rejection_log_path(),
        exc,
    )


_rejection_logger = DailyJsonLogger(
    directory=runtime_data_dir,
    prefix="classification_rejections",
    retention_days=REJECTION_LOG_RETENTION_DAYS,
    on_error=_rejection_log_error,
)


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


_CATEGORY_FIELD_PATTERN = re.compile(r'"category"\s*:\s*"([^"]*)"')


def _extract_rejection_slug_candidates(raw_output: str) -> set[str]:
    """Extract likely slug candidates from rejected model output.

    Only trusts output shaped like an actual category attempt: a completed
    ``"category":"..."`` JSON field (covers both single-object and batch
    array responses), or a bare single-token answer. Anything else -
    truncated fragments, prompt-echoed prose - is noise scattered with
    unrelated English words, not real category names, so it yields no
    candidates and is left to the raw rejection-event log instead.
    """
    candidates: set[str] = set()
    for match in _CATEGORY_FIELD_PATTERN.finditer(raw_output):
        normalized = _normalize_slug_token(match.group(1))
        if normalized and _is_high_signal_unmapped_candidate(normalized):
            candidates.add(normalized)
    if candidates:
        return candidates

    tokens = CANDIDATE_TOKEN_PATTERN.findall(raw_output)
    if len(tokens) != 1:
        return candidates

    normalized = _normalize_slug_token(tokens[0])
    if not normalized:
        return candidates
    if "_" not in normalized and len(normalized) < 4:
        return candidates
    if _is_high_signal_unmapped_candidate(normalized):
        candidates.add(normalized)
    return candidates


def _write_unmapped_categories(candidates: set[str]) -> int:
    """Merge rejected slug candidates into unmapped_categories.json.

    Returns the number of newly-added slugs.
    """
    if not candidates:
        return 0

    log_path = runtime_data_dir() / "unmapped_categories.json"
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
        try:
            log_path.write_text(json.dumps(sorted(existing), indent=2) + "\n")
        except OSError as exc:
            logger.warning("Failed to write unmapped categories to %s: %s", log_path, exc)
            return 0
    return added


def _get_rejection_log_path() -> Path:
    """Return today's date-stamped rejection log path."""
    return _rejection_logger.path_for()


def _rotate_rejection_logs() -> None:
    """Delete classification rejection logs older than retention window."""
    _rejection_logger.rotate(force=True)


def _append_rejection_events(events: list[dict[str, str]]) -> None:
    """Append non-tokenizable classification rejections for review."""
    _rejection_logger.log_many(events)
