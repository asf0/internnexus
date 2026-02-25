"""CSV export for test mode."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.cleanup.metadata import (
    _fetch_jobs_chunk,
    _get_metadata_result,
    _merge_location_results,
)
from pipeline.cleanup.parser import _parse_location_only
from pipeline.location.simple_parser import normalize_state_name
from pipeline.repositories.sqlalchemy_repo import SQLAlchemyJobRepository

logger = logging.getLogger(__name__)


async def _get_total_count(repo: SQLAlchemyJobRepository, since, process_all) -> int:
    return await repo.get_total_count(since=since, process_all=process_all)


async def _process_test_mode_chunked(session: AsyncSession, since, process_all, limit: int | None) -> int:
    repo = SQLAlchemyJobRepository(session)
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    csv_path = output_dir / "location_test_results.csv"

    unique_locations: dict[str, dict] = {}
    total_processed = 0
    chunk_size = 5000

    total_count = await _get_total_count(repo, since, process_all)
    logger.info(f"Found {total_count} jobs to process")

    logger.info("Building unique location cache and writing to CSV...")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
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

        last_id = None
        while True:
            if limit and total_processed >= limit:
                break

            rows, ashby_map, greenhouse_map, lever_map = await _fetch_jobs_chunk(
                repo, since, process_all, last_id, chunk_size
            )
            if not rows:
                break

            last_id = rows[-1]["id"]
            batch_results = []

            for row in rows:
                if limit and total_processed >= limit:
                    break

                total_processed += 1
                location = row["location"]

                if not location:
                    continue

                if location not in unique_locations:
                    unique_locations[location] = await _parse_location_only(location)
                    if len(unique_locations) % 500 == 0:
                        logger.info(f"Normalized {len(unique_locations)} unique locations...")

                parsed_result = unique_locations[location]

                if parsed_result.get("state"):
                    parsed_result["state"] = normalize_state_name(parsed_result["state"])

                metadata_result, metadata_source = _get_metadata_result(row, ashby_map, greenhouse_map, lever_map)

                final_result, source_used = _merge_location_results(
                    location, parsed_result, metadata_result, metadata_source
                )

                batch_results.append(
                    {
                        "id": str(row["id"]),
                        "source": str(row["source"]),
                        "original_location": location or "",
                        "city": final_result["city"] or "",
                        "state": final_result["state"] or "",
                        "country": final_result["country"] or "",
                        "fix_source": source_used,
                    }
                )

            if batch_results:
                writer.writerows(batch_results)

            if total_processed % 5000 == 0:
                logger.info(f"Processed {total_processed}/{min(total_count, limit or total_count)} jobs...")

    logger.info(f"Normalized {len(unique_locations)} unique locations")
    logger.info(f"Processed {total_processed} jobs")
    logger.info(f"Results saved to {csv_path}")
    logger.info("Step 'cleanup' completed in test mode - no database changes")
    return total_processed
