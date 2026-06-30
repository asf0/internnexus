"""Focused regression tests for the database I/O remediation."""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from pipeline.cleanup.normalizer import _normalize_existing_states
from pipeline.domain import JobSchema
from pipeline.ingest.result import IngestResult, SourceFetchStats
from pipeline.ingest.upsert import _changed_only_job_upsert, _job_rows, upsert_jobs
from pipeline.runtime.runner import _assess_sync_safety
from pipeline.runtime import services as runtime_services
from pipeline.sources.greenhouse import GreenhouseClient


def _job(**overrides) -> JobSchema:
    values = {
        "source": "greenhouse",
        "title": "Software Engineer Intern",
        "company": "Example",
        "location": "Remote",
        "apply_url": "https://example.com/jobs/1",
        "description_text": "A sufficiently long internship description for embedding.",
    }
    values.update(overrides)
    return JobSchema(**values)


def _sync_config():
    return SimpleNamespace(
        min_total_sighting_ratio=0.5,
        min_source_sighting_ratio=0.5,
        min_stale_guard_count=1000,
        min_fetched_to_stale_ratio=0.5,
    )


def test_ingest_result_metadata_round_trip() -> None:
    result = IngestResult(
        sync_id=uuid4(),
        total_fetched=30,
        source_counts={"greenhouse": 10, "lever": 10, "ashby": 10},
        fetch_error_counts={"greenhouse": 0, "lever": 1, "ashby": 0},
        source_complete={"greenhouse": True, "lever": False, "ashby": True},
        jobs_changed=4,
    )

    assert IngestResult.from_metadata(result.to_metadata()) == result


def test_source_fetch_stats_only_treats_404_as_authoritative_empty() -> None:
    stats = SourceFetchStats(source="greenhouse", configured_slugs=2)
    stats.record_error("http_404")
    assert stats.complete is True

    stats.record_error("http_error")
    assert stats.complete is False
    assert stats.fetch_errors == 2


def test_greenhouse_normalizer_accepts_null_location_name() -> None:
    client = object.__new__(GreenhouseClient)

    jobs = client._normalize_jobs(
        "example",
        [
            {
                "id": 123,
                "title": "Software Engineer Intern",
                "location": {"name": None},
                "absolute_url": "https://example.com/jobs/123",
                "content": "A sufficiently detailed job description.",
            }
        ],
    )

    assert len(jobs) == 1
    assert jobs[0].location == ""


def test_changed_only_upsert_contains_material_difference_guard() -> None:
    rows, _ = _job_rows([_job()])
    statement = _changed_only_job_upsert(rows)
    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert "ON CONFLICT (fingerprint) DO UPDATE" in sql
    assert "WHERE jobs.title IS DISTINCT FROM excluded.title" in sql
    assert "jobs.description_text IS DISTINCT FROM excluded.description_text" in sql
    assert "jobs.job_type IS DISTINCT FROM excluded.job_type" in sql
    assert "jobs.work_mode IS DISTINCT FROM excluded.work_mode" in sql
    assert "jobs.is_active IS NOT true" in sql
    assert "last_seen" in sql
    assert sql.count("embedding_skip_reason") >= 2


class _RowCountResult:
    rowcount = 0


class _StatementCaptureSession:
    def __init__(self):
        self.statements = []

    async def execute(self, statement, _parameters=None):
        self.statements.append(statement)
        return _RowCountResult()

    async def commit(self):
        return None


@pytest.mark.asyncio
async def test_location_trimming_skips_already_normalized_rows() -> None:
    session = _StatementCaptureSession()

    await _normalize_existing_states(session)

    trim_statements = [str(statement) for statement in session.statements[:3]]
    assert all("IS DISTINCT FROM TRIM" in statement for statement in trim_statements)


class _FakeExecuteResult:
    def __init__(self, rows=None):
        self._rows = rows or []

    def fetchall(self):
        return list(self._rows)


class _FakeSession:
    def __init__(self):
        self.statements = []
        self.commits = 0

    async def execute(self, statement):
        self.statements.append(statement)
        if len(self.statements) % 2 == 0:
            return _FakeExecuteResult([("changed-job",)])
        return _FakeExecuteResult()

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        return None

    def expunge_all(self):
        return None


@pytest.mark.asyncio
async def test_sighting_and_job_upsert_commit_atomically_per_batch() -> None:
    session = _FakeSession()
    sync_id = uuid4()

    stats = await upsert_jobs(
        session,
        [_job()],
        sync_id=sync_id,
        batch_size=100,
    )

    assert len(session.statements) == 2
    assert "pipeline_job_sightings" in str(session.statements[0])
    assert "ON CONFLICT" in str(session.statements[1])
    assert session.commits == 1
    assert stats.seen == 1
    assert stats.changed == 1


class _FailingJobUpsertSession(_FakeSession):
    def __init__(self):
        super().__init__()
        self.rollbacks = 0

    async def execute(self, statement):
        self.statements.append(statement)
        if len(self.statements) == 2:
            raise RuntimeError("job upsert failed")
        return _FakeExecuteResult()

    async def rollback(self):
        self.rollbacks += 1


@pytest.mark.asyncio
async def test_sighting_transaction_rolls_back_when_job_upsert_fails() -> None:
    session = _FailingJobUpsertSession()

    with pytest.raises(RuntimeError, match="job upsert failed"):
        await upsert_jobs(
            session,
            [_job()],
            sync_id=uuid4(),
            batch_size=100,
        )

    assert len(session.statements) == 2
    assert session.commits == 0
    assert session.rollbacks == 1


def test_sync_safety_rejects_incomplete_source_before_mutation() -> None:
    ingest = IngestResult(
        sync_id=uuid4(),
        total_fetched=100,
        source_counts={"greenhouse": 100, "lever": 0, "ashby": 0},
        fetch_error_counts={"greenhouse": 0, "lever": 1, "ashby": 0},
        source_complete={"greenhouse": True, "lever": False, "ashby": True},
    )

    assessment = _assess_sync_safety(
        ingest,
        source_counts=ingest.source_counts,
        previous_source_counts=None,
        stale_count=10,
        config=_sync_config(),
    )

    assert assessment.safe is False
    assert any("incomplete sources" in reason for reason in assessment.reasons)


def test_sync_safety_accepts_complete_plausible_run() -> None:
    ingest = IngestResult(
        sync_id=uuid4(),
        total_fetched=270_000,
        source_counts={"greenhouse": 90_000, "lever": 90_000, "ashby": 90_000},
        fetch_error_counts={"greenhouse": 0, "lever": 0, "ashby": 0},
        source_complete={"greenhouse": True, "lever": True, "ashby": True},
    )

    assessment = _assess_sync_safety(
        ingest,
        source_counts=ingest.source_counts,
        previous_source_counts={"greenhouse": 91_000, "lever": 89_000, "ashby": 90_000},
        stale_count=1_500,
        config=_sync_config(),
    )

    assert assessment.safe is True
    assert assessment.reasons == ()


def test_sync_safety_rejects_large_per_source_drop() -> None:
    ingest = IngestResult(
        sync_id=uuid4(),
        total_fetched=190_000,
        source_counts={"greenhouse": 10_000, "lever": 90_000, "ashby": 90_000},
        fetch_error_counts={"greenhouse": 0, "lever": 0, "ashby": 0},
        source_complete={"greenhouse": True, "lever": True, "ashby": True},
    )

    assessment = _assess_sync_safety(
        ingest,
        source_counts=ingest.source_counts,
        previous_source_counts={"greenhouse": 90_000, "lever": 90_000, "ashby": 90_000},
        stale_count=80_000,
        config=_sync_config(),
    )

    assert assessment.safe is False
    assert any("greenhouse sightings" in reason for reason in assessment.reasons)


@pytest.mark.asyncio
async def test_standalone_ingest_uses_explicit_context_and_cleans_sightings(
    monkeypatch,
) -> None:
    ingest = IngestResult.empty(uuid4())
    cleaned = []

    @asynccontextmanager
    async def _lock():
        yield

    class _Runner:
        dry_run = False

        async def step_ingest(self, state):
            assert state is None
            return ingest

        async def cleanup_sync_sightings(self, sync_id):
            cleaned.append(sync_id)

    monkeypatch.setattr(runtime_services, "job_sync_lock", _lock)
    await runtime_services.run_selected_step(
        _Runner(),
        SimpleNamespace(step="ingest", delete_inactive=False, test=False, limit=None),
    )

    assert cleaned == [ingest.sync_id]


@pytest.mark.asyncio
async def test_standalone_delete_without_synchronization_context_is_rejected(
    monkeypatch,
) -> None:
    @asynccontextmanager
    async def _lock():
        yield

    monkeypatch.setattr(runtime_services, "job_sync_lock", _lock)
    with pytest.raises(ValueError, match="requires run-scoped sightings"):
        await runtime_services.run_selected_step(
            SimpleNamespace(),
            SimpleNamespace(
                step="delete_inactive",
                delete_inactive=False,
                test=False,
                limit=None,
            ),
        )
