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


def _sync_config():
    return SimpleNamespace(
        min_total_sighting_ratio=0.5,
        min_source_sighting_ratio=0.5,
        min_stale_guard_count=1000,
        min_fetched_to_stale_ratio=0.5,
    )


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


@pytest.mark.asyncio
async def test_finalize_sync_uses_run_scoped_session_for_sightings() -> None:
    ingest = IngestResult.empty(uuid4())
    run_session = object()
    observed: dict[str, object] = {}

    class _State:
        session = run_session

        async def mark_step_complete(self, *_args, **_kwargs):
            return None

    runner = PipelineRunner()

    async def assess(received, session=None):
        observed["assess_session"] = session
        return SyncSafetyAssessment(
            safe=False,
            reasons=("test stop",),
            stale_count=0,
            source_counts={"greenhouse": 0, "lever": 0, "ashby": 0},
            previous_source_counts=None,
        )

    async def cleanup(sync_id, session=None):
        observed["cleanup_session"] = session
        observed["sync_id"] = sync_id

    runner.assess_sync = assess
    runner.cleanup_sync_sightings = cleanup

    assert await runner.finalize_sync(_State(), ingest) == (0, 0)
    assert observed == {
        "assess_session": run_session,
        "cleanup_session": run_session,
        "sync_id": ingest.sync_id,
    }


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
