"""CSV export for test mode."""

from __future__ import annotations

import asyncio
import csv
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.stages.cleanup.loop import CleanupRecord, run_cleanup_loop
from pipeline.repositories.sqlalchemy_repo import SQLAlchemyJobRepository
from pipeline.infra.lru import LRUDict
from pipeline.infra.paths import OUTPUT_DIR

logger = logging.getLogger(__name__)


def _write_csv_header(csv_path: Path) -> None:
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "id",
                "source",
                "original_location",
                "city",
                "state",
                "country",
                "fix_source",
            ],
        )
        writer.writeheader()


def _append_csv_rows(csv_path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    with open(csv_path, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "id",
                "source",
                "original_location",
                "city",
                "state",
                "country",
                "fix_source",
            ],
        )
        writer.writerows(rows)


async def _process_test_mode_chunked(
    session: AsyncSession,
    since,
    process_all,
    limit: int | None,
    chunk_size: int = 5000,
    location_cache_max_size: int = 10_000,
) -> int:
    repo = SQLAlchemyJobRepository(session)
    output_dir = OUTPUT_DIR
    output_dir.mkdir(exist_ok=True)

    csv_path = output_dir / "location_test_results.csv"

    location_cache: LRUDict[str, dict] = LRUDict(max_size=location_cache_max_size)

    logger.info("Building unique location cache and writing to CSV...")

    await asyncio.to_thread(_write_csv_header, csv_path)

    async def emit(records: list[CleanupRecord]) -> int:
        rows = [
            {
                "id": str(r.job_id),
                "source": r.source,
                "original_location": r.original_location or "",
                "city": r.city or "",
                "state": r.state or "",
                "country": r.country or "",
                "fix_source": r.fix_source,
            }
            for r in records
        ]
        if rows:
            await asyncio.to_thread(_append_csv_rows, csv_path, rows)
        return len(rows)

    async def _prepare_noop(_locations: list[str]) -> None:
        # This command intentionally bypasses unknown-location preparation.
        pass

    stats = await run_cleanup_loop(
        repo=repo,
        since=since,
        process_all=process_all,
        chunk_size=chunk_size,
        location_cache=location_cache,
        emit=emit,
        prepare_unknown=_prepare_noop,
        after_batch=None,
        limit=limit,
    )

    logger.info(f"Normalized {stats.unique_locations} unique locations")
    logger.info(f"Processed {stats.processed} jobs")
    logger.info(f"Results saved to {csv_path}")
    logger.info("Step 'cleanup' completed in test mode - no database changes")
    return stats.processed
