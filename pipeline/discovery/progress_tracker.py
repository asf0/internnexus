"""Progress tracking for incremental discovery."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .browser_config import OUTPUT_DIR, PROGRESS_FILE

logger = logging.getLogger(__name__)


def load_progress(file_path: Path | None = None) -> dict[str, Any]:
    """Load discovery progress from file.

    Returns progress data or default structure if no file exists.
    """
    if file_path is None:
        output_dir = Path(__file__).parent / OUTPUT_DIR
        file_path = output_dir / PROGRESS_FILE

    default_progress = {
        "metadata": {
            "last_batch": 0,
            "total_batches": 0,
            "last_updated": None,
            "status": "not_started",
            "current_delay": 5.0,
        },
        "completed_queries": [],
        "companies": {
            "lever": [],
            "greenhouse": [],
            "ashby": [],
        },
    }

    if not file_path.exists():
        return default_progress

    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            for key in default_progress:
                if key not in data:
                    data[key] = default_progress[key]
            return data
    except Exception as e:
        logger.warning(f"Could not load progress file: {e}")
        return default_progress


def save_progress(
    progress: dict[str, Any],
    file_path: Path | None = None,
) -> None:
    """Save discovery progress to file."""
    if file_path is None:
        output_dir = Path(__file__).parent / OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / PROGRESS_FILE

    progress["metadata"]["last_updated"] = datetime.utcnow().isoformat()

    try:
        with open(file_path, "w") as f:
            json.dump(progress, f, indent=2)
        logger.info(f"Progress saved: {progress['metadata']['status']}")
    except Exception as e:
        logger.error(f"Failed to save progress: {e}")


def mark_query_complete(
    progress: dict[str, Any],
    country: str,
    board: str,
) -> None:
    """Mark a query as completed."""
    query_key = f"{country}|{board}"
    if query_key not in progress["completed_queries"]:
        progress["completed_queries"].append(query_key)
        progress["metadata"]["last_batch"] = len(progress["completed_queries"])


def is_query_complete(
    progress: dict[str, Any],
    country: str,
    board: str,
) -> bool:
    """Check if a query has already been completed."""
    query_key = f"{country}|{board}"
    return query_key in progress["completed_queries"]


def add_companies(
    progress: dict[str, Any],
    board: str,
    companies: set[str],
) -> int:
    """Add companies to progress, return count of new companies."""
    if board not in progress["companies"]:
        progress["companies"][board] = []

    existing = set(progress["companies"][board])
    new_companies = companies - existing

    if new_companies:
        progress["companies"][board] = sorted(list(existing | new_companies))
        return len(new_companies)

    return 0


def get_remaining_queries(
    progress: dict[str, Any],
    all_queries: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    """Get list of queries that haven't been completed yet."""
    remaining = []
    for country, board in all_queries:
        if not is_query_complete(progress, country, board):
            remaining.append((country, board))
    return remaining


def update_delay(progress: dict[str, Any], increase: bool = False) -> float:
    """Update and return current delay."""
    current_delay = progress["metadata"]["current_delay"]

    if increase:
        from .browser_config import DELAY_INCREASE_ON_BLOCK, MAX_DELAY_CAP

        current_delay = min(current_delay * DELAY_INCREASE_ON_BLOCK, MAX_DELAY_CAP)
        logger.warning(f"Increasing delay to {current_delay:.1f}s due to blocking")

    progress["metadata"]["current_delay"] = current_delay
    return current_delay
