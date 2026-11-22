"""Bootstrap/reconciliation dispatch and per-board accounting.

Given a fetched board, decide whether to bootstrap or reconcile it, guard
against suspicious mass drops, and accumulate run totals.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.domain.board_snapshot import build_board_snapshot
from pipeline.repositories.board_snapshots import (
    load_snapshot,
    persist_bootstrap_snapshot,
    reconcile_board,
)
from pipeline.stages.ingest.source_stream import BoardFetchResult
from pipeline.stages.ingest.upsert import upsert_jobs

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class IngestTotals:
    total_fetched: int = 0
    total_changed: int = 0
    total_deactivated: int = 0
    boards_fetched: int = 0
    boards_changed: int = 0
    boards_unchanged: int = 0
    boards_incomplete: int = 0


def is_suspicious_board_drop(
    previous_count: int,
    new_count: int,
    *,
    ratio: float,
    min_count: int,
) -> bool:
    """A board fetch is suspicious if it looks more like a scrape gap than a
    real closure: either it came back fully empty when it previously had
    jobs, or - for boards large enough that turnover noise doesn't dominate -
    it lost more than `ratio` of its previously known jobs in one fetch.
    """
    if previous_count <= 0:
        return False
    if new_count == 0:
        return True
    return previous_count >= min_count and new_count < previous_count * (1 - ratio)


async def _ingest_bootstrap_board(
    db: AsyncSession, board: BoardFetchResult, snapshot, *, sync_id: UUID, upsert_batch_size: int, totals: IngestTotals
) -> None:
    if board.jobs:
        upsert_stats = await upsert_jobs(
            db,
            list(snapshot.jobs_by_fingerprint.values()),
            sync_id=sync_id,
            deduplicate=False,
            batch_size=upsert_batch_size,
        )
        totals.total_changed += upsert_stats.changed
    await persist_bootstrap_snapshot(
        db,
        board.source,
        board.slug,
        snapshot,
    )
    totals.boards_changed += 1


async def _should_preserve_suspicious_drop(
    db: AsyncSession, board: BoardFetchResult, snapshot, *, ratio: float, min_count: int
) -> bool:
    current = await load_snapshot(db, board.source, board.slug)
    previous_count = current.job_count if current is not None else 0
    if not is_suspicious_board_drop(
        previous_count,
        snapshot.job_count,
        ratio=ratio,
        min_count=min_count,
    ):
        return False
    logger.warning(
        "Preserving snapshot for suspicious board drop %s/%s (%d -> %d jobs)",
        board.source,
        board.slug,
        previous_count,
        snapshot.job_count,
    )
    return True


async def _reconcile_ingest_board(
    db: AsyncSession,
    board: BoardFetchResult,
    snapshot,
    *,
    confirmed_retired: bool,
    upsert_batch_size: int,
    suspicious_drop_ratio: float,
    suspicious_drop_min_count: int,
    totals: IngestTotals,
) -> None:
    if not confirmed_retired and await _should_preserve_suspicious_drop(
        db, board, snapshot, ratio=suspicious_drop_ratio, min_count=suspicious_drop_min_count
    ):
        totals.boards_incomplete += 1
        return
    reconcile_stats = await reconcile_board(
        db,
        board.source,
        board.slug,
        snapshot,
        batch_size=upsert_batch_size,
    )
    totals.total_changed += reconcile_stats.changed
    totals.total_deactivated += reconcile_stats.deactivated
    if reconcile_stats.snapshot_changed:
        totals.boards_changed += 1
    else:
        totals.boards_unchanged += 1


async def process_ingest_board(
    db: AsyncSession,
    board: BoardFetchResult,
    *,
    bootstrap: bool,
    sync_id: UUID,
    upsert_batch_size: int,
    suspicious_drop_ratio: float,
    suspicious_drop_min_count: int,
    totals: IngestTotals,
) -> int:
    """Ingest one board and return the number of jobs it contributed."""
    totals.boards_fetched += 1
    confirmed_retired = bool(board.error and board.error.get("error_type") == "http_404_confirmed")
    if board.error is not None and not confirmed_retired:
        totals.boards_incomplete += 1
        return 0

    snapshot = build_board_snapshot(board.jobs)
    totals.total_fetched += len(board.jobs)

    if bootstrap:
        await _ingest_bootstrap_board(
            db, board, snapshot, sync_id=sync_id, upsert_batch_size=upsert_batch_size, totals=totals
        )
    else:
        await _reconcile_ingest_board(
            db,
            board,
            snapshot,
            confirmed_retired=confirmed_retired,
            upsert_batch_size=upsert_batch_size,
            suspicious_drop_ratio=suspicious_drop_ratio,
            suspicious_drop_min_count=suspicious_drop_min_count,
            totals=totals,
        )
    return len(board.jobs)
