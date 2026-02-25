"""Query timing middleware for SQLAlchemy."""

from __future__ import annotations

import logging
import time

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

SLOW_QUERY_THRESHOLD_MS = 100


def setup_query_timing(engine: AsyncEngine) -> None:
    """Set up query timing listeners for the given engine."""

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("query_start_time", []).append(time.perf_counter())

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total_time = time.perf_counter() - conn.info["query_start_time"].pop()
        total_ms = total_time * 1000

        if total_ms > SLOW_QUERY_THRESHOLD_MS:
            statement_short = statement.replace("\n", " ")[:200]
            logger.warning(f"[SLOW_QUERY] {total_ms:.1f}ms - {statement_short}")


def log_query_metrics(total_time_ms: float, query_count: int) -> None:
    """Log query metrics at the end of a request."""
    if query_count > 0:
        avg_time = total_time_ms / query_count
        logger.debug(
            f"[QUERY_METRICS] {query_count} queries, "
            f"{total_time_ms:.1f}ms total, {avg_time:.1f}ms avg"
        )
