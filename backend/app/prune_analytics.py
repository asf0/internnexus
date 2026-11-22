"""Retention cleanup for the mcp_invocations analytics table.

Run as a one-shot maintenance command (dry-run by default), the same way as
``app.rotate_resumes``::

    docker compose run --rm backend python -m app.prune_analytics --apply

Rows in ``mcp_invocations`` older than the retention window are deleted in
bounded batches. The table is leaf analytics (no inbound foreign keys), so the
delete is unconditional beyond the age cutoff.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.infra.config import get_settings
from app.infra.db import get_sync_engine
from app.models import MCPInvocation


def prune_mcp_invocations(
    *,
    retention_days: int,
    apply: bool,
    batch_size: int = 10_000,
    session_factory=None,
) -> int:
    """Delete mcp_invocations older than ``retention_days``.

    In dry-run mode (``apply=False``) nothing is deleted and the number of rows
    that *would* be removed is returned. When applying, rows are deleted in
    batches of ``batch_size`` and the total deleted count is returned.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, retention_days))
    batch_size = max(1, batch_size)
    make_session = session_factory or (lambda: Session(get_sync_engine()))

    with make_session() as session:
        if not apply:
            candidate = session.scalar(
                select(func.count())
                .select_from(MCPInvocation)
                .where(MCPInvocation.invoked_at < cutoff)
            )
            session.rollback()
            return int(candidate or 0)

        total = 0
        while True:
            expired_ids = session.scalars(
                select(MCPInvocation.id)
                .where(MCPInvocation.invoked_at < cutoff)
                .order_by(MCPInvocation.id)
                .limit(batch_size)
            ).all()
            if not expired_ids:
                break
            result = session.execute(
                delete(MCPInvocation).where(MCPInvocation.id.in_(expired_ids))
            )
            session.commit()
            total += int(getattr(result, "rowcount", 0) or 0)
            if len(expired_ids) < batch_size:
                break
        return total


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(
        description="Prune old mcp_invocations analytics rows (dry-run by default)."
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=settings.mcp_invocation_retention_days,
        help="Delete rows older than this many days (default from settings).",
    )
    parser.add_argument("--apply", action="store_true", help="Persist the deletions")
    parser.add_argument("--batch-size", type=int, default=10_000)
    args = parser.parse_args()
    if args.retention_days < 1:
        parser.error("--retention-days must be at least 1")
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")

    count = prune_mcp_invocations(
        retention_days=args.retention_days,
        apply=args.apply,
        batch_size=args.batch_size,
    )
    mode = "deleted" if args.apply else "would delete (dry-run)"
    print(f"mcp_invocations prune {mode}: {count} rows older than {args.retention_days}d")


if __name__ == "__main__":
    main()
