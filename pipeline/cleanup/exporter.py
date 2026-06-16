"""CSV export for test mode."""

from __future__ import annotations

import asyncio
import csv
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.cleanup.metadata import (
    _merge_location_results,
)
from pipeline.cleanup.parser import _parse_location_only
from pipeline.location.simple_parser import normalize_state_name
from pipeline.repositories.sqlalchemy_repo import SQLAlchemyJobRepository
from pipeline.utils.lru import LRUDict

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


async def _get_total_count(repo: SQLAlchemyJobRepository, since, process_all) -> int:
    return await repo.get_total_count(since=since, process_all=process_all)


async def _process_test_mode_chunked(
    session: AsyncSession,
    since,
    process_all,
    limit: int | None,
    location_cache_max_size: int = 50_000,
) -> int:
    repo = SQLAlchemyJobRepository(session)
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    csv_path = output_dir / "location_test_results.csv"

    unique_locations: LRUDict[str, dict] = LRUDict(max_size=location_cache_max_size)
    total_processed = 0
    chunk_size = 5000

    total_count = await _get_total_count(repo, since, process_all)
    logger.info(f"Found {total_count} jobs to process")

    logger.info("Building unique location cache and writing to CSV...")

    await asyncio.to_thread(_write_csv_header, csv_path)

    last_id = None
    while True:
        if limit and total_processed >= limit:
            break

        jobs = await repo.fetch_jobs_batch_keyset(
            since=since,
            process_all=process_all,
            last_id=last_id,
            limit=chunk_size,
        )
        if not jobs:
            break

        last_id = jobs[-1].id
        batch_results = []

        for job in jobs:
            if limit and total_processed >= limit:
                break

            total_processed += 1
            location = job.location

            if not location:
                continue

            if location not in unique_locations:
                cache_size_before = len(unique_locations)
                unique_locations[location] = await _parse_location_only(location)
                if len(unique_locations) // 500 > cache_size_before // 500:
                    logger.info(f"Normalized {len(unique_locations)} unique locations...")

            parsed_result = unique_locations[location]

            if parsed_result.get("state"):
                parsed_result["state"] = normalize_state_name(parsed_result["state"])

            final_result, source_used = _merge_location_results(
                location, parsed_result, None, "fallback"
            )

            batch_results.append(
                {
                    "id": str(job.id),
                    "source": str(job.source),
                    "original_location": location or "",
                    "city": final_result["city"] or "",
                    "state": final_result["state"] or "",
                    "country": final_result["country"] or "",
                    "fix_source": source_used,
                }
            )

        if batch_results:
            await asyncio.to_thread(_append_csv_rows, csv_path, batch_results)

        if total_processed % 5000 == 0:
            logger.info(f"Processed {total_processed}/{min(total_count, limit or total_count)} jobs...")

    logger.info(f"Normalized {len(unique_locations)} unique locations")
    logger.info(f"Processed {total_processed} jobs")
    logger.info(f"Results saved to {csv_path}")
    logger.info("Step 'cleanup' completed in test mode - no database changes")
    return total_processed
