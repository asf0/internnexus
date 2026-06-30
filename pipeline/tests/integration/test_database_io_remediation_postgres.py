"""PostgreSQL row-version regression tests for changed-only ingestion.

Set PIPELINE_TEST_DATABASE_URL to a migrated disposable PostgreSQL database to
run this suite. The tests use an outer transaction and leave no committed rows.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from pipeline.domain import JobSchema
from pipeline.ingest.identity import fingerprint_for
from pipeline.ingest.result import IngestResult
from pipeline.ingest.upsert import upsert_jobs
from pipeline.repositories import LocationUpdate
from pipeline.repositories.sightings import (
    count_stale_jobs,
    delete_sightings,
    get_previous_successful_source_counts,
    prune_abandoned_sightings,
)
from pipeline.repositories.sqlalchemy_repo import SQLAlchemyJobRepository
from pipeline.repositories.sync_ops import (
    batched_delete_inactive,
    batched_mark_stale_jobs_inactive,
)
from pipeline.runtime.runner import PipelineRunner
from pipeline.runtime.state import PipelineStateManager


TEST_DATABASE_URL = os.getenv("PIPELINE_TEST_DATABASE_URL")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not TEST_DATABASE_URL,
        reason="PIPELINE_TEST_DATABASE_URL is not configured",
    ),
]


@pytest.fixture
async def postgres_session():
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.connect() as connection:
        migrated = await connection.scalar(text("SELECT to_regclass('public.pipeline_job_sightings') IS NOT NULL"))
        await connection.rollback()
        if not migrated:
            await engine.dispose()
            pytest.skip("test database has not been upgraded to the sightings migration")

        transaction = await connection.begin()
        factory = async_sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        async with factory() as session:
            yield session
        await transaction.rollback()
    await engine.dispose()


def _job(
    apply_url: str,
    *,
    description: str,
    title: str = "Database I/O Intern",
    **overrides,
) -> JobSchema:
    values = {
        "source": "greenhouse",
        "title": title,
        "company": "I/O Test",
        "location": "Remote",
        "apply_url": apply_url,
        "description_text": description,
        "job_category": "software_engineering",
    }
    values.update(overrides)
    return JobSchema(**values)


async def _row_version(session, fingerprint: str):
    return (
        await session.execute(
            text(
                """
                SELECT
                    xmin::text,
                    ctid::text,
                    search_vector::text,
                    job_category,
                    description_embedding IS NULL AS embedding_is_null
                FROM jobs
                WHERE fingerprint = :fingerprint
                """
            ),
            {"fingerprint": fingerprint},
        )
    ).one()


@pytest.mark.asyncio
async def test_identical_ingest_preserves_xmin_and_ctid(postgres_session) -> None:
    apply_url = f"https://example.invalid/io-test/{uuid4()}"
    job = _job(
        apply_url,
        description="This description is long enough to produce a stable search vector.",
    )
    fingerprint = fingerprint_for(job)

    first_sync = uuid4()
    inserted = await upsert_jobs(
        postgres_session,
        [job],
        sync_id=first_sync,
        batch_size=10,
    )
    before = await _row_version(postgres_session, fingerprint)

    duplicate_sighting = await upsert_jobs(
        postgres_session,
        [job, job],
        sync_id=first_sync,
        batch_size=10,
    )
    unchanged = await upsert_jobs(
        postgres_session,
        [job],
        sync_id=uuid4(),
        batch_size=10,
    )
    after = await _row_version(postgres_session, fingerprint)
    first_sync_sightings = await postgres_session.scalar(
        text(
            """
            SELECT count(*)
            FROM pipeline_job_sightings
            WHERE sync_id = :sync_id
              AND fingerprint = :fingerprint
            """
        ),
        {"sync_id": first_sync, "fingerprint": fingerprint},
    )

    assert inserted.changed == 1
    assert duplicate_sighting.seen == 1
    assert duplicate_sighting.changed == 0
    assert first_sync_sightings == 1
    assert unchanged.changed == 0
    assert after.xmin == before.xmin
    assert after.ctid == before.ctid
    assert after.search_vector == before.search_vector


@pytest.mark.asyncio
async def test_description_change_creates_one_row_version_and_invalidates_category(
    postgres_session,
) -> None:
    apply_url = f"https://example.invalid/io-test/{uuid4()}"
    original = _job(
        apply_url,
        description="Original database engineering internship description.",
    )
    fingerprint = fingerprint_for(original)
    await upsert_jobs(postgres_session, [original], sync_id=uuid4(), batch_size=10)
    await postgres_session.execute(
        text(
            """
            UPDATE jobs
            SET description_embedding = array_fill(0.0::real, ARRAY[2560])::vector
            WHERE fingerprint = :fingerprint
            """
        ),
        {"fingerprint": fingerprint},
    )
    await postgres_session.commit()
    before = await _row_version(postgres_session, fingerprint)
    before_matches_changed_term = await postgres_session.scalar(
        text(
            """
            SELECT search_vector @@ plainto_tsquery('english', 'distributed')
            FROM jobs
            WHERE fingerprint = :fingerprint
            """
        ),
        {"fingerprint": fingerprint},
    )

    changed = _job(
        apply_url,
        description="Changed distributed systems internship description.",
    )
    stats = await upsert_jobs(postgres_session, [changed], sync_id=uuid4(), batch_size=10)
    after = await _row_version(postgres_session, fingerprint)
    after_matches_changed_term = await postgres_session.scalar(
        text(
            """
            SELECT search_vector @@ plainto_tsquery('english', 'distributed')
            FROM jobs
            WHERE fingerprint = :fingerprint
            """
        ),
        {"fingerprint": fingerprint},
    )

    assert stats.changed == 1
    assert (after.xmin, after.ctid) != (before.xmin, before.ctid)
    assert before.embedding_is_null is False
    assert after.embedding_is_null is True
    assert before_matches_changed_term is False
    assert after_matches_changed_term is True
    assert after.search_vector != before.search_vector
    assert after.job_category is None


@pytest.mark.asyncio
async def test_title_change_clears_embedding_skip_markers_and_category(
    postgres_session,
) -> None:
    apply_url = f"https://example.invalid/io-test/{uuid4()}"
    original = _job(
        apply_url,
        description="A stable description whose title will change.",
    )
    fingerprint = fingerprint_for(original)
    await upsert_jobs(postgres_session, [original], sync_id=uuid4(), batch_size=10)
    await postgres_session.execute(
        text(
            """
            UPDATE jobs
            SET embedding_skip_reason = 'too_short',
                embedding_skipped_at = now()
            WHERE fingerprint = :fingerprint
            """
        ),
        {"fingerprint": fingerprint},
    )
    await postgres_session.commit()

    changed = _job(
        apply_url,
        description=original.description_text,
        title="Distributed Database I/O Intern",
    )
    stats = await upsert_jobs(postgres_session, [changed], sync_id=uuid4(), batch_size=10)
    row = (
        await postgres_session.execute(
            text(
                """
                SELECT embedding_skip_reason, embedding_skipped_at, job_category
                FROM jobs
                WHERE fingerprint = :fingerprint
                """
            ),
            {"fingerprint": fingerprint},
        )
    ).one()

    assert stats.changed == 1
    assert row.embedding_skip_reason is None
    assert row.embedding_skipped_at is None
    assert row.job_category is None


@pytest.mark.asyncio
async def test_reactivation_and_nullable_material_field_changes(postgres_session) -> None:
    apply_url = f"https://example.invalid/io-test/{uuid4()}"
    original = _job(
        apply_url,
        description="A job used to test reactivation and nullable fields.",
        job_type="internship",
    )
    fingerprint = fingerprint_for(original)
    await upsert_jobs(postgres_session, [original], sync_id=uuid4(), batch_size=10)
    await postgres_session.execute(
        text("UPDATE jobs SET is_active = false WHERE fingerprint = :fingerprint"),
        {"fingerprint": fingerprint},
    )
    await postgres_session.commit()

    posted_at = datetime(2026, 6, 29, tzinfo=timezone.utc)
    changed = _job(
        apply_url,
        description=original.description_text,
        job_type="full_time",
        posted_at=posted_at,
    )
    changed_stats = await upsert_jobs(
        postgres_session,
        [changed],
        sync_id=uuid4(),
        batch_size=10,
    )
    reactivated = (
        await postgres_session.execute(
            text(
                """
                SELECT is_active, job_type::text, posted_at
                FROM jobs
                WHERE fingerprint = :fingerprint
                """
            ),
            {"fingerprint": fingerprint},
        )
    ).one()

    cleared = _job(
        apply_url,
        description=original.description_text,
        job_type=None,
        posted_at=None,
    )
    cleared_stats = await upsert_jobs(
        postgres_session,
        [cleared],
        sync_id=uuid4(),
        batch_size=10,
    )
    cleared_row = (
        await postgres_session.execute(
            text(
                """
                SELECT job_type::text, posted_at
                FROM jobs
                WHERE fingerprint = :fingerprint
                """
            ),
            {"fingerprint": fingerprint},
        )
    ).one()

    assert changed_stats.changed == 1
    assert reactivated.is_active is True
    assert reactivated.job_type == "full_time"
    assert reactivated.posted_at == posted_at
    assert cleared_stats.changed == 1
    assert cleared_row.job_type is None
    assert cleared_row.posted_at is None


@pytest.mark.asyncio
async def test_sightings_sync_preserves_seen_and_manual_jobs_and_deletes_stale(
    postgres_session,
) -> None:
    current_sync = uuid4()
    previous_sync = uuid4()
    seen = _job(
        f"https://example.invalid/io-test/{uuid4()}",
        description="A currently observed job description.",
    )
    stale = _job(
        f"https://example.invalid/io-test/{uuid4()}",
        description="A job that disappeared from the source.",
    )
    manual = JobSchema(
        source="manual",
        title="Manual internship",
        company="I/O Test",
        location="Remote",
        apply_url=f"https://example.invalid/io-test/{uuid4()}",
        description_text="A manually managed job that synchronization must preserve.",
    )

    await upsert_jobs(postgres_session, [stale, manual], sync_id=previous_sync, batch_size=10)
    await upsert_jobs(postgres_session, [seen], sync_id=current_sync, batch_size=10)

    stale_before = await count_stale_jobs(postgres_session, current_sync)
    marked = await batched_mark_stale_jobs_inactive(
        postgres_session,
        current_sync,
        batch_size=100,
    )
    states = dict(
        (
            await postgres_session.execute(
                text(
                    """
                    SELECT fingerprint, is_active
                    FROM jobs
                    WHERE fingerprint = ANY(:fingerprints)
                    """
                ),
                {
                    "fingerprints": [
                        fingerprint_for(seen),
                        fingerprint_for(stale),
                        fingerprint_for(manual),
                    ]
                },
            )
        ).all()
    )

    assert stale_before >= 1
    assert marked >= 1
    assert states[fingerprint_for(seen)] is True
    assert states[fingerprint_for(stale)] is False
    assert states[fingerprint_for(manual)] is True

    deleted = await batched_delete_inactive(
        postgres_session,
        current_sync,
        batch_size=100,
    )
    remaining = set(
        (
            await postgres_session.execute(
                text(
                    """
                    SELECT fingerprint
                    FROM jobs
                    WHERE fingerprint = ANY(:fingerprints)
                    """
                ),
                {
                    "fingerprints": [
                        fingerprint_for(seen),
                        fingerprint_for(stale),
                        fingerprint_for(manual),
                    ]
                },
            )
        ).scalars()
    )

    assert deleted >= 1
    assert fingerprint_for(seen) in remaining
    assert fingerprint_for(stale) not in remaining
    assert fingerprint_for(manual) in remaining

    cleaned = await delete_sightings(postgres_session, current_sync)
    remaining_sightings = await postgres_session.scalar(
        text("SELECT count(*) FROM pipeline_job_sightings WHERE sync_id = :sync_id"),
        {"sync_id": current_sync},
    )
    assert cleaned == 1
    assert remaining_sightings == 0


@pytest.mark.asyncio
async def test_sighting_retention_preserves_resumable_runs_and_skips_unsafe_baselines(
    postgres_session,
) -> None:
    running_sync = uuid4()
    abandoned_sync = uuid4()
    unsafe_run = uuid4()
    safe_run = uuid4()
    safe_counts = {"greenhouse": 90, "lever": 80, "ashby": 70}
    unsafe_results = {
        "source_counts": {"greenhouse": 1, "lever": 1, "ashby": 1},
        "source_complete": {"greenhouse": True, "lever": True, "ashby": True},
        "sync_skipped_reasons": ["test guard"],
    }
    safe_results = {
        "source_counts": safe_counts,
        "source_complete": {"greenhouse": True, "lever": True, "ashby": True},
    }
    await postgres_session.execute(
        text(
            """
            INSERT INTO pipeline_runs (id, status, started_at, completed_at, results)
            VALUES
                (:running_sync, 'running', now() - interval '8 days', NULL, NULL),
                (:unsafe_run, 'completed', now(), now(), :unsafe_results),
                (
                    :safe_run,
                    'completed',
                    now() - interval '1 day',
                    now() - interval '1 day',
                    :safe_results
                )
            """
        ),
        {
            "running_sync": running_sync,
            "unsafe_run": unsafe_run,
            "safe_run": safe_run,
            "unsafe_results": json.dumps(unsafe_results),
            "safe_results": json.dumps(safe_results),
        },
    )
    await postgres_session.execute(
        text(
            """
            INSERT INTO pipeline_job_sightings
                (sync_id, fingerprint, source, created_at)
            VALUES
                (:running_sync, :running_fingerprint, 'greenhouse', now() - interval '8 days'),
                (:abandoned_sync, :abandoned_fingerprint, 'greenhouse', now() - interval '8 days')
            """
        ),
        {
            "running_sync": running_sync,
            "running_fingerprint": str(uuid4()),
            "abandoned_sync": abandoned_sync,
            "abandoned_fingerprint": str(uuid4()),
        },
    )
    await postgres_session.commit()

    baseline = await get_previous_successful_source_counts(
        postgres_session,
        exclude_sync_id=uuid4(),
    )
    pruned = await prune_abandoned_sightings(
        postgres_session,
        retention_days=7,
        batch_size=1,
    )
    remaining_syncs = set(
        (
            await postgres_session.execute(
                text(
                    """
                    SELECT DISTINCT sync_id
                    FROM pipeline_job_sightings
                    WHERE sync_id = ANY(:sync_ids)
                    """
                ),
                {"sync_ids": [running_sync, abandoned_sync]},
            )
        ).scalars()
    )

    assert baseline == safe_counts
    assert pruned == 1
    assert running_sync in remaining_syncs
    assert abandoned_sync not in remaining_syncs


class _BorrowedSession:
    """Expose one transaction-bound session without allowing helpers to close it."""

    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, _exc_type, _exc, _tb):
        return None

    async def close(self):
        return None

    def __getattr__(self, name):
        return getattr(self._session, name)


def _use_borrowed_session(monkeypatch, session) -> None:
    def factory():
        return _BorrowedSession(session)

    monkeypatch.setattr(
        "pipeline.repositories.sqlalchemy_repo.AsyncSessionLocal",
        factory,
    )
    monkeypatch.setattr(
        "pipeline.cleanup.batch_processor.AsyncSessionLocal",
        factory,
    )


@pytest.mark.asyncio
async def test_incomplete_source_run_performs_no_stale_mutation(
    postgres_session,
    monkeypatch,
) -> None:
    sync_id = uuid4()
    stale = _job(
        f"https://example.invalid/io-test/{uuid4()}",
        description="This job must remain active after an incomplete fetch.",
    )
    seen = _job(
        f"https://example.invalid/io-test/{uuid4()}",
        description="This job was observed during the incomplete fetch.",
    )
    await upsert_jobs(postgres_session, [stale], sync_id=uuid4(), batch_size=10)
    await upsert_jobs(postgres_session, [seen], sync_id=sync_id, batch_size=10)
    ingest = IngestResult(
        sync_id=sync_id,
        total_fetched=1,
        source_counts={"greenhouse": 1, "lever": 0, "ashby": 0},
        fetch_error_counts={"greenhouse": 0, "lever": 1, "ashby": 0},
        source_complete={"greenhouse": True, "lever": False, "ashby": True},
        jobs_changed=1,
    )
    _use_borrowed_session(monkeypatch, postgres_session)

    marked, deleted = await PipelineRunner().finalize_sync(None, ingest)
    stale_active = await postgres_session.scalar(
        text("SELECT is_active FROM jobs WHERE fingerprint = :fingerprint"),
        {"fingerprint": fingerprint_for(stale)},
    )

    assert marked == 0
    assert deleted == 0
    assert stale_active is True


@pytest.mark.asyncio
async def test_failed_post_ingest_run_resumes_with_same_sightings(
    postgres_session,
    monkeypatch,
) -> None:
    sync_id = uuid4()
    job = _job(
        f"https://example.invalid/io-test/{uuid4()}",
        description="A sighting retained across a failed post-ingest run.",
    )
    ingest = IngestResult(
        sync_id=sync_id,
        total_fetched=1,
        source_counts={"greenhouse": 1, "lever": 0, "ashby": 0},
        fetch_error_counts={"greenhouse": 0, "lever": 0, "ashby": 0},
        source_complete={"greenhouse": True, "lever": True, "ashby": True},
        jobs_changed=1,
    )
    await upsert_jobs(postgres_session, [job], sync_id=sync_id, batch_size=10)
    await postgres_session.execute(
        text(
            """
            INSERT INTO pipeline_runs
                (id, status, step_completed, started_at, completed_at, results)
            VALUES
                (:sync_id, 'failed', 'ingest', now(), now(), :results)
            """
        ),
        {
            "sync_id": sync_id,
            "results": json.dumps(ingest.to_metadata()),
        },
    )
    await postgres_session.commit()

    state = PipelineStateManager(run_id=sync_id)
    state._session = postgres_session
    resumed_id = await state.start_run()
    persisted_results = await postgres_session.scalar(
        text("SELECT results FROM pipeline_runs WHERE id = :sync_id"),
        {"sync_id": sync_id},
    )
    resumed = IngestResult.from_metadata(json.loads(persisted_results))
    _use_borrowed_session(monkeypatch, postgres_session)

    assert resumed_id == sync_id
    assert resumed == ingest
    marked, deleted = await PipelineRunner().finalize_sync(state, resumed)
    status = await postgres_session.scalar(
        text("SELECT status::text FROM pipeline_runs WHERE id = :sync_id"),
        {"sync_id": sync_id},
    )
    sighting_count = await postgres_session.scalar(
        text("SELECT count(*) FROM pipeline_job_sightings WHERE sync_id = :sync_id"),
        {"sync_id": sync_id},
    )
    job_exists = await postgres_session.scalar(
        text("SELECT count(*) FROM jobs WHERE fingerprint = :fingerprint"),
        {"fingerprint": fingerprint_for(job)},
    )

    assert marked == 0
    assert deleted == 0
    assert status == "running"
    assert sighting_count == 0
    assert job_exists == 1


@pytest.mark.asyncio
async def test_location_cleanup_updates_job_and_search_vector_once(
    postgres_session,
) -> None:
    job = _job(
        f"https://example.invalid/io-test/{uuid4()}",
        description="A job used to verify single-source search maintenance.",
    )
    fingerprint = fingerprint_for(job)
    await upsert_jobs(postgres_session, [job], sync_id=uuid4(), batch_size=10)
    before = await _row_version(postgres_session, fingerprint)
    job_id = await postgres_session.scalar(
        text("SELECT id FROM jobs WHERE fingerprint = :fingerprint"),
        {"fingerprint": fingerprint},
    )
    await postgres_session.execute(text("CREATE TEMP TABLE io_job_updates (calls integer)"))
    await postgres_session.execute(
        text(
            """
            CREATE FUNCTION pg_temp.audit_io_job_update()
            RETURNS trigger AS $$
            BEGIN
                INSERT INTO io_job_updates VALUES (1);
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
    )
    await postgres_session.execute(
        text(
            """
            CREATE TRIGGER io_job_update_audit
            AFTER UPDATE ON jobs
            FOR EACH ROW EXECUTE FUNCTION pg_temp.audit_io_job_update()
            """
        )
    )
    await postgres_session.commit()

    repo = SQLAlchemyJobRepository(postgres_session)
    updated = await repo.update_job_locations(
        [
            LocationUpdate(
                job_id=job_id,
                city="Denver",
                state="Colorado",
                country="United States",
                is_remote=False,
            )
        ]
    )
    after = await _row_version(postgres_session, fingerprint)
    update_calls = await postgres_session.scalar(text("SELECT count(*) FROM io_job_updates"))

    assert updated == 1
    assert update_calls == 1
    assert after.search_vector != before.search_vector
