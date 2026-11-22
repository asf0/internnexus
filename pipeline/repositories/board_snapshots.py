"""Persistence and atomic reconciliation for canonical ATS board snapshots."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import exists, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.domain.board_snapshot import BoardSnapshot, canonical_json
from pipeline.repositories.job_upsert import build_job_rows, changed_only_job_upsert
from pipeline.repositories.job_text_sql import rowcount as _rowcount
from pipeline.infra.models import Job, JobBoardSnapshot, JobSource, PipelineSyncState
from pipeline.infra.job_cache import invalidate_job_detail_cache
from pipeline.infra.pipeline_config import get_config

SYNC_STATE_ID = 1

# Manifest entries for a fingerprint missing from the latest fetch are tagged
# with this prefix (never a valid hex sha256 digest) instead of being
# deactivated immediately, so a single scrape gap doesn't read as a closure.
# Deactivation only happens once a fingerprint is *still* missing on the next
# reconcile, i.e. it's already tagged pending.
_PENDING_PREFIX = "pending:"


@dataclass(frozen=True, slots=True)
class BoardReconcileStats:
    changed: int = 0
    deactivated: int = 0
    snapshot_changed: bool = False


def _snapshot_upsert(
    source: JobSource,
    company_slug: str,
    snapshot: BoardSnapshot,
):
    now = datetime.now(timezone.utc)
    statement = insert(JobBoardSnapshot).values(
        source=source,
        company_slug=company_slug,
        board_hash=snapshot.board_hash,
        manifest=snapshot.manifest,
        job_count=snapshot.job_count,
        changed_at=now,
    )
    return statement.on_conflict_do_update(
        index_elements=[
            JobBoardSnapshot.source,
            JobBoardSnapshot.company_slug,
        ],
        set_={
            "board_hash": statement.excluded.board_hash,
            "manifest": statement.excluded.manifest,
            "job_count": statement.excluded.job_count,
            "changed_at": statement.excluded.changed_at,
        },
    )


async def is_bootstrap_complete(session: AsyncSession) -> bool:
    result = await session.execute(
        select(PipelineSyncState.snapshots_bootstrapped).where(PipelineSyncState.id == SYNC_STATE_ID)
    )
    return bool(result.scalar_one_or_none())


async def mark_bootstrap_complete(session: AsyncSession) -> None:
    """Durably mark the one-time snapshot bootstrap as complete."""
    now = datetime.now(timezone.utc)
    statement = insert(PipelineSyncState).values(
        id=SYNC_STATE_ID,
        snapshots_bootstrapped=True,
        snapshots_bootstrapped_at=now,
    )
    statement = statement.on_conflict_do_update(
        index_elements=[PipelineSyncState.id],
        set_={
            "snapshots_bootstrapped": True,
            "snapshots_bootstrapped_at": now,
        },
    )
    try:
        await session.execute(statement)
        await session.commit()
    except Exception:
        await session.rollback()
        raise


async def load_snapshot(
    session: AsyncSession,
    source: JobSource | str,
    company_slug: str,
    *,
    for_update: bool = False,
) -> JobBoardSnapshot | None:
    statement = select(JobBoardSnapshot).where(
        JobBoardSnapshot.source == JobSource(source),
        JobBoardSnapshot.company_slug == company_slug,
    )
    if for_update:
        statement = statement.with_for_update()
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def persist_bootstrap_snapshot(
    session: AsyncSession,
    source: JobSource | str,
    company_slug: str,
    snapshot: BoardSnapshot,
) -> None:
    """Persist one resumable bootstrap snapshot without reconciling jobs."""
    try:
        await session.execute(_snapshot_upsert(JobSource(source), company_slug, snapshot))
        await session.commit()
    except Exception:
        await session.rollback()
        raise


def _not_present_on_another_board(
    source: JobSource,
    company_slug: str,
):
    return ~exists(
        select(JobBoardSnapshot.source).where(
            JobBoardSnapshot.manifest.op("?")(Job.fingerprint),
            ~((JobBoardSnapshot.source == source) & (JobBoardSnapshot.company_slug == company_slug)),
        )
    )


async def reconcile_board(
    session: AsyncSession,
    source: JobSource | str,
    company_slug: str,
    snapshot: BoardSnapshot,
    *,
    batch_size: int | None = None,
) -> BoardReconcileStats:
    """Atomically reconcile one successfully fetched board without sightings.

    An unchanged hash returns after the locking read, creating no writes and no
    commit. Changed boards batch statements for bounded parameter sizes while
    retaining a single transaction and commit. A fingerprint missing from this
    fetch is deactivated only once it's been missing for two consecutive
    reconciles (see `_PENDING_PREFIX`), so a single scrape gap doesn't read as
    a closure.
    """
    normalized_source = JobSource(source)
    # The outer job-sync advisory lock serializes reconcilers. Avoid
    # SELECT FOR UPDATE here: tuple locks can dirty heap pages and emit WAL,
    # which would defeat the zero-write unchanged-board path.
    current = await load_snapshot(session, normalized_source, company_slug)
    if current is not None and current.board_hash == snapshot.board_hash:
        return BoardReconcileStats()

    if batch_size is None:
        batch_size = get_config().ingest.upsert_batch_size
    batch_size = max(1, batch_size)

    old_manifest = current.manifest if current is not None else {}
    changed_fingerprints = [
        fingerprint
        for fingerprint, content_hash in snapshot.manifest.items()
        if old_manifest.get(fingerprint) != content_hash
    ]
    missing_fingerprints = old_manifest.keys() - snapshot.manifest.keys()

    # First miss: carry the fingerprint forward into the persisted manifest
    # (tagged pending) instead of deactivating. Second consecutive miss: it's
    # already tagged, so it's genuinely gone.
    already_pending = {
        fingerprint for fingerprint in missing_fingerprints if old_manifest[fingerprint].startswith(_PENDING_PREFIX)
    }
    newly_missing = missing_fingerprints - already_pending
    removed_fingerprints = list(already_pending)

    changed = 0
    deactivated = 0
    changed_ids = []
    try:
        for start in range(0, len(changed_fingerprints), batch_size):
            fingerprints = changed_fingerprints[start : start + batch_size]
            jobs = [snapshot.jobs_by_fingerprint[value] for value in fingerprints]
            rows, _ = build_job_rows(jobs)
            result = await session.execute(changed_only_job_upsert(rows))
            ids = [row[0] for row in result.fetchall()]
            changed_ids.extend(ids)
            changed += len(ids)

        other_board_guard = _not_present_on_another_board(
            normalized_source,
            company_slug,
        )
        for start in range(0, len(removed_fingerprints), batch_size):
            fingerprints = removed_fingerprints[start : start + batch_size]
            result = await session.execute(
                update(Job)
                .where(
                    Job.fingerprint.in_(fingerprints),
                    Job.is_active.is_(True),
                    other_board_guard,
                )
                .values(is_active=False)
                .returning(Job.id)
            )
            ids = [row[0] for row in result.fetchall()]
            changed_ids.extend(ids)
            # Production UPDATE ... RETURNING yields IDs. The lightweight unit
            # double models only rowcount, so retain that equivalent fallback.
            deactivated += len(ids) or _rowcount(result)

        persisted_snapshot = snapshot
        if newly_missing:
            persisted_manifest = dict(snapshot.manifest)
            for fingerprint in newly_missing:
                persisted_manifest[fingerprint] = _PENDING_PREFIX + old_manifest[fingerprint]
            persisted_snapshot = BoardSnapshot(
                board_hash=hashlib.sha256(canonical_json(persisted_manifest)).hexdigest(),
                manifest=persisted_manifest,
                jobs_by_fingerprint=snapshot.jobs_by_fingerprint,
            )

        await session.execute(_snapshot_upsert(normalized_source, company_slug, persisted_snapshot))
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    await invalidate_job_detail_cache(changed_ids)

    return BoardReconcileStats(
        changed=changed,
        deactivated=deactivated,
        snapshot_changed=True,
    )
