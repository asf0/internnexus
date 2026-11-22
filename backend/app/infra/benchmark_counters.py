"""Opt-in process-local counters for job-detail cache benchmarks."""

from __future__ import annotations

from collections import Counter
from threading import Lock

from app.infra.config import get_settings

_counters: Counter[str] = Counter()
_lock = Lock()


def record(name: str) -> None:
    """Increment a benchmark counter only when explicitly enabled."""
    if not get_settings().benchmark_counters_enabled:
        return
    with _lock:
        _counters[name] += 1


def snapshot() -> dict[str, int]:
    with _lock:
        return dict(_counters)
