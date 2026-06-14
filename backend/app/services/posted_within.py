from __future__ import annotations

from datetime import datetime, timedelta

POSTED_WITHIN_WINDOWS: dict[str, timedelta] = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}
POSTED_WITHIN_VALUES = tuple(POSTED_WITHIN_WINDOWS)


def posted_within_cutoff(value: str, now: datetime) -> datetime | None:
    window = POSTED_WITHIN_WINDOWS.get(value)
    if window is None:
        return None
    return now - window
