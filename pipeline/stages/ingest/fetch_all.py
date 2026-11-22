"""Streamed ingestion orchestration.

Sequences the ATS sources, fetches each concurrently (``source_stream``),
processes boards (``board_processing``), and assembles the run result. The
slug-404 cooldown cache lives in ``slug_cooldown``.
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.domain.sync_result import IngestResult, SourceFetchStats
from pipeline.repositories.board_snapshots import is_bootstrap_complete
from pipeline.repositories.sync_ops import (
    SYNC_BATCH_SIZE,
    batched_mark_stale_jobs_inactive,
)
from pipeline.stages.ingest.board_processing import IngestTotals, process_ingest_board
from pipeline.stages.ingest.source_stream import fetch_source_jobs_streamed
from pipeline.stages.ingest.sources.registry import get_greenhouse_slugs, get_lever_slugs, get_ashby_slugs
from pipeline.stages.ingest.sources.greenhouse import GreenhouseClient
from pipeline.stages.ingest.sources.lever import LeverClient
from pipeline.stages.ingest.sources.ashby import AshbyClient
from pipeline.stages.ingest.sources.protocols import JobSourceClient
from pipeline.infra.pipeline_config import get_config

logger = logging.getLogger(__name__)


def _close_api_clients(*clients: JobSourceClient) -> None:
    """Best-effort close for ATS clients."""
    for client in clients:
        close = getattr(client, "close", None)
        if callable(close):
            try:
                close()
            except Exception as exc:  # noqa: BLE001  # client close is best-effort
                logger.warning("Failed to close %s client: %s", client.__class__.__name__, exc)


async def fetch_and_ingest_streamed(
    db: AsyncSession,
    *,
    chunk_size: int,
    upsert_batch_size: int,
    api_fetch_concurrency: int,
    not_found_cooldown_hours: int,
    sync_id: UUID,
) -> IngestResult:
    """Fetch and reconcile company boards with zero writes when unchanged."""
    ingest_config = get_config().ingest
    gh_slugs = get_greenhouse_slugs()
    lever_slugs = get_lever_slugs()
    ashby_slugs = get_ashby_slugs()

    logger.info(
        "Fetching %d Greenhouse, %d Lever, %d Ashby companies in streamed chunks of %d slugs...",
        len(gh_slugs),
        len(lever_slugs),
        len(ashby_slugs),
        chunk_size,
    )

    greenhouse: JobSourceClient = GreenhouseClient()
    lever: JobSourceClient = LeverClient()
    ashby: JobSourceClient = AshbyClient()

    totals = IngestTotals()
    bootstrap = not await is_bootstrap_complete(db)
    source_stats: dict[str, SourceFetchStats] = {}
    try:
        for source_name, slugs, client in (
            ("Greenhouse", gh_slugs, greenhouse),
            ("Lever", lever_slugs, lever),
            ("Ashby", ashby_slugs, ashby),
        ):
            source_key = source_name.lower()
            stats = SourceFetchStats(source=source_key, configured_slugs=len(slugs))
            source_stats[source_key] = stats
            source_total = 0
            board_index = 0
            async for board in fetch_source_jobs_streamed(
                source_name=source_name,
                slugs=slugs,
                fetch_func=client.fetch_jobs,
                chunk_size=chunk_size,
                api_fetch_concurrency=api_fetch_concurrency,
                not_found_cooldown_hours=not_found_cooldown_hours,
                run_id=str(sync_id),
                stats=stats,
            ):
                board_index += 1
                source_total += await process_ingest_board(
                    db,
                    board,
                    bootstrap=bootstrap,
                    sync_id=sync_id,
                    upsert_batch_size=upsert_batch_size,
                    suspicious_drop_ratio=ingest_config.suspicious_drop_ratio,
                    suspicious_drop_min_count=ingest_config.suspicious_drop_min_count,
                    totals=totals,
                )
                del board
                await asyncio.sleep(0)
            logger.info(
                "Fetched %d %s jobs from %d board(s)",
                source_total,
                source_name,
                board_index,
            )
    finally:
        _close_api_clients(greenhouse, lever, ashby)

    logger.info(
        "Streamed ingestion complete: %d jobs processed, %d inserted/changed/reactivated",
        totals.total_fetched,
        totals.total_changed,
    )
    return IngestResult(
        sync_id=sync_id,
        total_fetched=totals.total_fetched,
        source_counts={source: stats.jobs_fetched for source, stats in source_stats.items()},
        fetch_error_counts={source: stats.fetch_errors for source, stats in source_stats.items()},
        source_complete={source: stats.complete for source, stats in source_stats.items()},
        jobs_changed=totals.total_changed,
        jobs_deactivated=totals.total_deactivated,
        snapshot_mode=not bootstrap,
        snapshot_bootstrap=bootstrap,
        boards_fetched=totals.boards_fetched,
        boards_changed=totals.boards_changed,
        boards_unchanged=totals.boards_unchanged,
        boards_incomplete=totals.boards_incomplete,
    )


async def mark_stale_jobs_inactive(
    session: AsyncSession,
    sync_id: UUID,
    batch_size: int | None = None,
    max_attempts: int | None = None,
    base_delay: float | None = None,
    max_delay: float | None = None,
) -> int:
    """Mark active non-manual jobs that were not seen this run as inactive.

    Uses the run-scoped sightings table to identify jobs not observed this run.

    Args:
        session: SQLAlchemy async session.
        sync_id: Synchronization run whose sightings define active jobs.
        batch_size: Number of rows per batch. Defaults to SYNC_BATCH_SIZE.
        max_attempts: Maximum retry attempts. Defaults to 3.
        base_delay: Base delay in seconds. Defaults to 0.5.
        max_delay: Maximum delay in seconds. Defaults to 4.0.

    Returns:
        Number of jobs marked inactive.
    """
    if batch_size is None:
        batch_size = SYNC_BATCH_SIZE
    return await batched_mark_stale_jobs_inactive(
        session,
        sync_id,
        batch_size=batch_size,
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
    )
