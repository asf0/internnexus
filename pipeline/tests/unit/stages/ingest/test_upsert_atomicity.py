"""Focused regression tests for the database I/O remediation."""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from pipeline.stages.cleanup.normalizer import _normalize_existing_states
from pipeline.domain import JobSchema
from pipeline.domain.sync_result import IngestResult, SourceFetchStats
from pipeline.repositories.job_upsert import build_job_rows, changed_only_job_upsert
from pipeline.stages.ingest.upsert import upsert_jobs
from internnexus_core.text import embedding_input_hash
from pipeline.runtime.orchestrator import PipelineRunner, SyncSafetyAssessment, _assess_sync_safety
from pipeline.runtime import services as runtime_services
from pipeline.stages.ingest.sources.greenhouse import GreenhouseClient


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


def test_source_fetch_stats_preserves_jobs_until_404_is_confirmed() -> None:
    stats = SourceFetchStats(source="greenhouse", configured_slugs=2)
    stats.record_error("http_404")
    assert stats.complete is False

    confirmed = SourceFetchStats(source="greenhouse", configured_slugs=1)
    confirmed.record_error("http_404_confirmed")
    assert confirmed.complete is True
    assert stats.fetch_errors == 1
    assert confirmed.fetch_errors == 1


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
    rows, _ = build_job_rows([_job()])
    statement = changed_only_job_upsert(rows)
    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert "ON CONFLICT (fingerprint) DO UPDATE" in sql
    assert "WHERE jobs.title IS DISTINCT FROM excluded.title" in sql
    assert "jobs.description_text IS DISTINCT FROM excluded.description_text" in sql
    assert "jobs.job_type IS DISTINCT FROM excluded.job_type" in sql
    assert "jobs.work_mode IS DISTINCT FROM excluded.work_mode" in sql
    assert "jobs.is_active IS NOT true" in sql
    assert "last_seen" in sql
    assert sql.count("embedding_skip_reason") >= 2
    assert "embedding_input_hash" in sql


def test_embedding_input_hash_ignores_html_and_whitespace_presentation() -> None:
    assert embedding_input_hash("<p>Build reliable systems</p>\n") == embedding_input_hash(
        "Build reliable systems"
    )


def test_upsert_uses_embedding_input_hash_for_normalized_description() -> None:
    rows, _ = build_job_rows([_job(description_text="<p>Build reliable systems</p>")])

    assert rows[0]["embedding_input_hash"] == embedding_input_hash("<p>Build reliable systems</p>")


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
