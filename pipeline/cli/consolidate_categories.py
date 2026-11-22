#!/usr/bin/env python3
"""Consolidate job categories in the database.

This script maps existing LLM-generated categories to the canonical set
using the mapping defined in category_mapping.py.

Usage:
    # Dry run to see what would change
    uv run python -m pipeline.cli.consolidate_categories --dry-run

    # Apply consolidation
    uv run python -m pipeline.cli.consolidate_categories

    # Show statistics only
    uv run python -m pipeline.cli.consolidate_categories --stats
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from collections import Counter
from typing import cast

import sys

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.stages.classification import CANONICAL_CATEGORIES, get_canonical_category
from pipeline.infra.logging_config import configure_logging
from pipeline.infra.db import AsyncSessionLocal
from pipeline.infra.models import Job

configure_logging()
logger = logging.getLogger(__name__)


async def get_category_stats(session: AsyncSession) -> dict[str, int]:
    """Get count of jobs per category."""
    result = await session.execute(
        select(Job.job_category, func.count(Job.id))
        .where(Job.job_category.isnot(None))
        .group_by(Job.job_category)
        .order_by(func.count(Job.id).desc())
    )
    return {cast(str, row[0]): row[1] for row in result.all() if row[0] is not None}


async def get_total_jobs(session: AsyncSession) -> int:
    """Get total job count."""
    result = await session.execute(func.count(Job.id))
    return result.scalar() or 0


async def get_null_count(session: AsyncSession) -> int:
    """Get count of jobs with NULL category."""
    result = await session.execute(select(func.count(Job.id)).where(Job.job_category.is_(None)))
    return result.scalar() or 0


async def analyze_consolidation(session: AsyncSession) -> dict:
    """Analyze what the consolidation would do."""
    stats = await get_category_stats(session)
    total_jobs = await get_total_jobs(session)
    null_count = await get_null_count(session)

    changes: dict[str, dict] = {}
    new_nulls = 0
    already_canonical = 0
    will_change = 0

    for original_cat, count in stats.items():
        canonical = get_canonical_category(original_cat)

        if canonical is None:
            new_nulls += count
            changes[original_cat] = {"action": "set_null", "count": count}
        elif canonical == original_cat.lower():
            already_canonical += count
            changes[original_cat] = {"action": "keep", "count": count, "canonical": canonical}
        else:
            will_change += count
            changes[original_cat] = {"action": "change", "count": count, "canonical": canonical}

    return {
        "total_jobs": total_jobs,
        "current_nulls": null_count,
        "new_nulls": new_nulls,
        "already_canonical": already_canonical,
        "will_change": will_change,
        "total_categories_before": len(stats),
        "total_categories_after": len(CANONICAL_CATEGORIES),
        "changes": changes,
    }


async def apply_consolidation(session: AsyncSession, batch_size: int = 1000) -> dict:
    """Apply category consolidation in primary-key/keyset batches."""
    if batch_size < 1:
        raise ValueError("batch_size must be greater than zero")

    stats_before = await get_category_stats(session)
    updated_counts = Counter()
    nullified = 0
    total_processed = 0

    for original_cat in stats_before:
        canonical = get_canonical_category(original_cat)
        if canonical is not None and canonical == original_cat.lower():
            continue
        changed = await _consolidate_category(session, original_cat, canonical, stats_before[original_cat], batch_size, total_processed)
        total_processed += changed
        if canonical is None:
            nullified += changed
        else:
            updated_counts[canonical] += changed

    stats_after = await get_category_stats(session)
    return {
        "nullified": nullified,
        "updated_counts": dict(updated_counts),
        "categories_before": len(stats_before),
        "categories_after": len(stats_after),
        "total_processed": total_processed,
    }


async def _consolidate_category(session: AsyncSession, original_cat: str, canonical: str | None, total: int, batch_size: int, total_processed: int) -> int:
    """Update one source category in keyset batches and return its changed count."""
    after_id = None
    category_processed = 0
    while True:
        stmt = select(Job.id).where(Job.job_category == original_cat).order_by(Job.id).limit(batch_size)
        if after_id is not None:
            stmt = stmt.where(Job.id > after_id)
        ids = list((await session.execute(stmt)).scalars().all())
        if not ids:
            return category_processed
        result = await session.execute(update(Job).where(Job.id.in_(ids), Job.job_category == original_cat).values(job_category=canonical))
        changed = int(getattr(result, "rowcount", 0) or 0)
        await session.commit()
        after_id = ids[-1]
        category_processed += changed
        logger.info("Consolidated %d/%d jobs for '%s' -> %s (%d total)", category_processed, total, original_cat, canonical or "NULL", total_processed + category_processed)


def print_analysis(analysis: dict) -> None:
    """Print consolidation analysis."""
    print("\n" + "=" * 70)
    print("CATEGORY CONSOLIDATION ANALYSIS")
    print("=" * 70)

    print(f"\nTotal jobs: {analysis['total_jobs']:,}")
    print(f"Jobs with NULL category: {analysis['current_nulls']:,}")
    print(f"Jobs already in canonical form: {analysis['already_canonical']:,}")
    print(f"Jobs that will change: {analysis['will_change']:,}")
    print(f"Jobs that will become NULL: {analysis['new_nulls']:,}")

    print(f"\nCategories before: {analysis['total_categories_before']}")
    print(f"Categories after: {analysis['total_categories_after']}")

    print("\n" + "-" * 70)
    print("TOP CHANGES BY COUNT:")
    print("-" * 70)

    sorted_changes = sorted(
        [(k, v) for k, v in analysis["changes"].items() if v["action"] == "change"],
        key=lambda x: x[1]["count"],
        reverse=True,
    )[:30]

    for original, info in sorted_changes:
        print(f"  {original:45} -> {info['canonical']:25} ({info['count']:,} jobs)")

    print("\n" + "-" * 70)
    print("CATEGORIES SET TO NULL:")
    print("-" * 70)

    null_changes = [(k, v) for k, v in analysis["changes"].items() if v["action"] == "set_null"]
    for original, info in null_changes:
        print(f"  {original:45} -> NULL ({info['count']:,} jobs)")

    print("\n" + "=" * 70)


def print_canonical_categories() -> None:
    """Print the canonical category list."""
    print("\n" + "=" * 70)
    print("CANONICAL CATEGORIES")
    print("=" * 70)

    for i, cat in enumerate(CANONICAL_CATEGORIES, 1):
        print(f"  {i:2}. {cat}")

    print(f"\nTotal: {len(CANONICAL_CATEGORIES)} categories")
    print("=" * 70)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Consolidate job categories in the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without making changes",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show current category statistics only",
    )
    parser.add_argument(
        "--list-canonical",
        action="store_true",
        help="List the canonical categories",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for updates (default: 1000)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Apply without interactive confirmation",
    )
    return parser.parse_args(argv)


async def _print_stats_mode(session: AsyncSession) -> int:
    """Query and print category statistics, then return 0."""
    stats = await get_category_stats(session)
    total = await get_total_jobs(session)
    nulls = await get_null_count(session)

    print("\n" + "=" * 70)
    print("CURRENT CATEGORY STATISTICS")
    print("=" * 70)
    print(f"\nTotal jobs: {total:,}")
    print(f"Jobs with NULL category: {nulls:,}")
    print(f"Jobs with category: {sum(stats.values()):,}")
    print(f"Unique categories: {len(stats)}")
    print("\nTop 50 categories:")
    print("-" * 70)
    for cat, count in list(stats.items())[:50]:
        print(f"  {cat:50} {count:8,}")
    print("=" * 70)
    return 0


async def _run_consolidation(
    session: AsyncSession,
    *,
    dry_run: bool,
    batch_size: int,
    assume_yes: bool = False,
) -> int:
    """Analyze, optionally confirm, and apply category consolidation."""
    logger.info("Analyzing categories...")
    analysis = await analyze_consolidation(session)

    print_analysis(analysis)

    if dry_run:
        print("\n*** DRY RUN - No changes made ***")
        return 0

    if not assume_yes:
        print("\nThis will make the changes shown above.")
        response = await asyncio.to_thread(input, "Continue? [y/N]: ")
        if response.lower() != "y":
            print("Aborted.")
            return 1

    logger.info("Applying consolidation...")
    result = await apply_consolidation(session, batch_size=batch_size)

    _print_apply_result(result)
    return 0


def _print_apply_result(result: dict) -> None:
    """Print the result of a consolidation apply."""
    print("\n" + "=" * 70)
    print("CONSOLIDATION COMPLETE")
    print("=" * 70)
    print(f"Jobs nullified: {result['nullified']:,}")
    print(f"Categories before: {result['categories_before']}")
    print(f"Categories after: {result['categories_after']}")

    if result["updated_counts"]:
        print("\nJobs per canonical category:")
        for cat, count in sorted(result["updated_counts"].items(), key=lambda x: -x[1]):
            print(f"  {cat:30} {count:8,}")

    print("=" * 70)


async def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.list_canonical:
        print_canonical_categories()
        return 0
    async with AsyncSessionLocal() as session:
        if args.stats:
            return await _print_stats_mode(session)
        return await _run_consolidation(
            session,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
            assume_yes=getattr(args, "yes", False),
        )


def cli() -> int:
    return asyncio.run(main())


if __name__ == "__main__":
    sys.exit(cli())
