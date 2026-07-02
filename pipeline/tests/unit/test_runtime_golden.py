"""Golden fixture tests for runtime/runner.py and runtime/state.py behavior.

Locks current observable behavior so every later PR in the runtime-repositories
refactor series can verify behavior preservation.

Covers:
 - _assess_sync_safety over ~12 representative inputs
 - _is_unsafe_delete_inactive_sync boundary values
 - PipelineStateManager state transitions (mocked AsyncSessionLocal)
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest

from pipeline.ingest.result import IngestResult
from pipeline.models import PipelineRunStatus
from pipeline.runtime.config import SyncConfig
from pipeline.runtime.runner import (
    PipelineRunner,
    SyncSafetyAssessment,
    _assess_sync_safety,
    _is_unsafe_delete_inactive_sync,
)
from pipeline.runtime.state import PipelineStateManager, clear_incomplete_runs


# -- Helpers --


def _ingest(total: int = 0, *, complete: bool = True) -> IngestResult:
    return IngestResult(
        sync_id=uuid4(),
        total_fetched=total,
        source_counts={"greenhouse": total, "lever": 0, "ashby": 0},
        fetch_error_counts={"greenhouse": 0, "lever": 0, "ashby": 0},
        source_complete={
            "greenhouse": complete,
            "lever": complete,
            "ashby": complete,
        },
    )


def _ingest_partial(complete_sources: set[str] | None = None) -> IngestResult:
    if complete_sources is None:
        complete_sources = {"greenhouse"}
    return IngestResult(
        sync_id=uuid4(),
        total_fetched=100,
        source_counts={"greenhouse": 100, "lever": 0, "ashby": 0},
        fetch_error_counts={"greenhouse": 0, "lever": 0, "ashby": 0},
        source_complete={
            "greenhouse": "greenhouse" in complete_sources,
            "lever": "lever" in complete_sources,
            "ashby": "ashby" in complete_sources,
        },
    )


def _default_sync_config() -> SyncConfig:
    return SyncConfig()


# -- PipelineRunner sequencing --


@pytest.mark.asyncio
async def test_pipeline_runner_preserves_step_sequence(monkeypatch) -> None:
    import pipeline.runtime.runner as runner_module

    calls: list[str] = []

    async def _no_incomplete_run():
        return None

    @asynccontextmanager
    async def _no_lock():
        yield

    async def _cleanup_resources(_label):
        return None

    runner = PipelineRunner(
        dry_run=True,
        get_incomplete_run_func=_no_incomplete_run,
    )

    async def _discover(_state):
        calls.append("discover")
        return 3

    async def _sync_inactive(_state):
        calls.append("sync_inactive")
        return 0

    async def _ingest_step(_state):
        calls.append("ingest")
        return _ingest(total=4)

    async def _finalize(_state, _ingest_result):
        calls.append("finalize_sync")
        return 2, 1

    async def _cleanup(_state, **_kwargs):
        calls.append("cleanup")
        return 5

    async def _classify(_state, **_kwargs):
        calls.append("classify")
        return 6, 1

    async def _embed(_state):
        calls.append("embed")
        return 7, 1

    runner.step_discover = _discover
    runner.step_sync_inactive = _sync_inactive
    runner.step_ingest = _ingest_step
    runner.finalize_sync = _finalize
    runner.step_cleanup = _cleanup
    runner.step_classify = _classify
    runner.step_embed = _embed
    monkeypatch.setattr(runner_module, "job_sync_lock", _no_lock)
    monkeypatch.setattr(runner_module, "cleanup_step_resources", _cleanup_resources)

    result = await runner.run()

    assert calls == [
        "discover",
        "sync_inactive",
        "ingest",
        "finalize_sync",
        "cleanup",
        "classify",
        "embed",
    ]
    assert result["companies_verified"] == 3
    assert result["jobs_fetched"] == 4
    assert result["jobs_marked_inactive"] == 2
    assert result["inactive_jobs_deleted"] == 1


# -- _assess_sync_safety tests --


class TestAssessSyncSafety:
    """Golden tests for _assess_sync_safety covering safe/unsafe/boundary inputs."""

    def test_safe_when_all_complete_and_good_ratios(self) -> None:
        ingest = _ingest(total=500)
        assessment = _assess_sync_safety(
            ingest,
            source_counts={"greenhouse": 500, "lever": 0, "ashby": 0},
            previous_source_counts=None,
            stale_count=0,
            config=_default_sync_config(),
        )
        assert assessment.safe is True
        assert assessment.reasons == ()

    def test_unsafe_incomplete_source(self) -> None:
        ingest = _ingest_partial(complete_sources={"greenhouse"})
        assessment = _assess_sync_safety(
            ingest,
            source_counts={"greenhouse": 100, "lever": 0, "ashby": 0},
            previous_source_counts=None,
            stale_count=0,
            config=_default_sync_config(),
        )
        assert assessment.safe is False
        assert any("incomplete sources" in r for r in assessment.reasons)

    def test_unsafe_zero_persisted_sightings(self) -> None:
        ingest = _ingest(total=0)
        assessment = _assess_sync_safety(
            ingest,
            source_counts={"greenhouse": 0, "lever": 0, "ashby": 0},
            previous_source_counts=None,
            stale_count=0,
            config=_default_sync_config(),
        )
        assert assessment.safe is False
        assert any("no persisted sightings" in r for r in assessment.reasons)

    def test_unsafe_total_drop_below_ratio(self) -> None:
        ingest = _ingest(total=100)
        assessment = _assess_sync_safety(
            ingest,
            source_counts={"greenhouse": 100, "lever": 0, "ashby": 0},
            previous_source_counts={"greenhouse": 1000, "lever": 0, "ashby": 0},
            stale_count=0,
            config=_default_sync_config(),
        )
        assert assessment.safe is False
        assert any("total sightings" in r for r in assessment.reasons)

    def test_unsafe_per_source_drop(self) -> None:
        ingest = _ingest(total=500)
        assessment = _assess_sync_safety(
            ingest,
            source_counts={"greenhouse": 500, "lever": 10, "ashby": 0},
            previous_source_counts={"greenhouse": 500, "lever": 200, "ashby": 0},
            stale_count=0,
            config=_default_sync_config(),
        )
        assert assessment.safe is False
        assert any("lever sightings" in r for r in assessment.reasons)

    def test_unsafe_stale_ratio_too_low(self) -> None:
        ingest = _ingest(total=50)
        config = _default_sync_config()
        assessment = _assess_sync_safety(
            ingest,
            source_counts={"greenhouse": 50, "lever": 0, "ashby": 0},
            previous_source_counts=None,
            stale_count=config.min_stale_guard_count,
            config=config,
        )
        assert assessment.safe is False
        assert any("sighting/stale ratio" in r for r in assessment.reasons)

    def test_safe_at_exact_boundary_ratio(self) -> None:
        """At exactly 50% of previous, should be safe (>= threshold)."""
        ingest = _ingest(total=500)
        assessment = _assess_sync_safety(
            ingest,
            source_counts={"greenhouse": 500, "lever": 0, "ashby": 0},
            previous_source_counts={"greenhouse": 1000, "lever": 0, "ashby": 0},
            stale_count=0,
            config=_default_sync_config(),
        )
        assert assessment.safe is True

    def test_ignores_zero_previous_source_count(self) -> None:
        """A source with 0 previous count should not trigger per-source drop."""
        ingest = _ingest(total=500)
        assessment = _assess_sync_safety(
            ingest,
            source_counts={"greenhouse": 500, "lever": 0, "ashby": 0},
            previous_source_counts={"greenhouse": 1000, "lever": 0, "ashby": 0},
            stale_count=0,
            config=_default_sync_config(),
        )
        assert assessment.safe is True

    def test_no_previous_baseline_skips_comparison(self) -> None:
        """When previous_source_counts is None, skip all previous-comparison checks."""
        ingest = _ingest(total=10)
        assessment = _assess_sync_safety(
            ingest,
            source_counts={"greenhouse": 10, "lever": 0, "ashby": 0},
            previous_source_counts=None,
            stale_count=0,
            config=_default_sync_config(),
        )
        assert assessment.safe is True

    def test_multiple_reasons_collected(self) -> None:
        ingest = _ingest_partial(complete_sources={"greenhouse"})
        assessment = _assess_sync_safety(
            ingest,
            source_counts={"greenhouse": 0, "lever": 0, "ashby": 0},
            previous_source_counts={"greenhouse": 1000, "lever": 0, "ashby": 0},
            stale_count=0,
            config=_default_sync_config(),
        )
        assert assessment.safe is False
        assert len(assessment.reasons) >= 2

    def test_custom_config_thresholds_apply(self) -> None:
        """Custom SyncConfig values should be respected."""
        ingest = _ingest(total=500)
        config = SyncConfig(min_total_sighting_ratio=0.9, min_source_sighting_ratio=0.9)
        assessment = _assess_sync_safety(
            ingest,
            source_counts={"greenhouse": 500, "lever": 0, "ashby": 0},
            previous_source_counts={"greenhouse": 1000, "lever": 0, "ashby": 0},
            stale_count=0,
            config=config,
        )
        assert assessment.safe is False
        assert any("total sightings" in r for r in assessment.reasons)

    def test_stale_below_guard_skips_ratio_check(self) -> None:
        """When stale < min_stale_guard_count, stale ratio is not checked."""
        ingest = _ingest(total=1)
        assessment = _assess_sync_safety(
            ingest,
            source_counts={"greenhouse": 1, "lever": 0, "ashby": 0},
            previous_source_counts=None,
            stale_count=999,  # below default min_stale_guard_count=1000
            config=_default_sync_config(),
        )
        assert assessment.safe is True


# -- _is_unsafe_delete_inactive_sync tests --


class TestIsUnsafeDeleteInactiveSync:
    """Golden tests for legacy _is_unsafe_delete_inactive_sync boundary values."""

    def test_safe_when_no_inactive_marked(self) -> None:
        assert _is_unsafe_delete_inactive_sync(0, 100) is False

    def test_unsafe_when_zero_fetched(self) -> None:
        assert _is_unsafe_delete_inactive_sync(100, 0) is True

    def test_safe_below_guard_threshold(self) -> None:
        assert _is_unsafe_delete_inactive_sync(999, 100) is False

    def test_unsafe_when_ratio_below_threshold(self) -> None:
        assert _is_unsafe_delete_inactive_sync(1000, 100) is True

    def test_safe_when_ratio_above_threshold(self) -> None:
        assert _is_unsafe_delete_inactive_sync(1000, 1000) is False


# -- PipelineStateManager tests --


class _FakePipelineRun:
    """Minimal fake PipelineRun for state manager tests."""

    def __init__(self, run_id=None, status="running", step_completed=None, results=None):
        self.id = run_id or uuid4()
        self.status = status
        self.step_completed = step_completed
        self.results = results
        self.error_message = None
        self.error_step = None
        self.completed_at = None
        self.started_at = None


class _FakeSession:
    """Minimal async session mock for PipelineStateManager tests."""

    def __init__(self):
        self.runs: dict = {}
        self.next_id = 0
        self.closed = False
        self.entered = False

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, *args):
        self.closed = True

    async def get(self, model, run_id):
        return self.runs.get(run_id)

    async def execute(self, stmt):
        return SimpleNamespace(
            scalar_one_or_none=lambda: None,
            fetchall=lambda: [],
        )

    def add(self, obj):
        if not hasattr(obj, "id") or obj.id is None:
            self.next_id += 1
            obj.id = uuid4()

    async def flush(self):
        if hasattr(self, "_pending"):
            for obj in self._pending:
                if not hasattr(obj, "id") or obj.id is None:
                    self.next_id += 1
                    obj.id = uuid4()
                self.runs[obj.id] = obj

    async def commit(self):
        pass


class TestPipelineStateManager:
    """Golden tests for PipelineStateManager state transitions."""

    def test_get_resume_step_from_none(self) -> None:
        from pipeline.runtime.steps import PIPELINE_STEPS

        manager = PipelineStateManager()
        run = _FakePipelineRun(step_completed=None)
        assert manager.get_resume_step(run) == PIPELINE_STEPS[0]

    def test_get_resume_step_after_ingest(self) -> None:
        run = _FakePipelineRun(step_completed="ingest")
        manager = PipelineStateManager()
        assert manager.get_resume_step(run) == "delete_inactive"

    def test_get_resume_step_after_last_step(self) -> None:
        from pipeline.runtime.steps import PIPELINE_STEPS

        last_step = PIPELINE_STEPS[-1]
        run = _FakePipelineRun(step_completed=last_step)
        manager = PipelineStateManager()
        assert manager.get_resume_step(run) is None

    def test_get_resume_step_unknown_step(self) -> None:
        run = _FakePipelineRun(step_completed="nonexistent_step")
        manager = PipelineStateManager()
        assert manager.get_resume_step(run) is None

    def test_require_session_raises_when_not_initialized(self) -> None:
        manager = PipelineStateManager()
        with pytest.raises(RuntimeError, match="session not initialized"):
            manager._require_session()

    def test_context_manager_enters_and_exits_session(self) -> None:
        """Verify the async context manager protocol."""
        manager = PipelineStateManager()
        assert manager._session is None

        async def run_test():
            async with manager:
                assert manager._session is not None
            assert manager._session is None

        # Patch AsyncSessionLocal to return our fake
        import pipeline.runtime.state as state_module

        fake = _FakeSession()

        original = state_module.AsyncSessionLocal

        class _FakeFactory:
            def __call__(self):
                return fake

        state_module.AsyncSessionLocal = _FakeFactory()
        try:
            import asyncio

            asyncio.run(run_test())
        finally:
            state_module.AsyncSessionLocal = original

    def test_start_run_creates_new_run_id(self) -> None:
        """When no run_id is provided, start_run should produce one."""
        import pipeline.runtime.state as state_module

        manager = PipelineStateManager()
        fake = _FakeSession()

        async def _fake_get(model, run_id):
            return None

        fake.get = _fake_get

        async def run_test():
            manager._session = fake
            run_id = await manager.start_run()
            assert run_id is not None
            assert manager.run_id == run_id

        original = state_module.AsyncSessionLocal

        class _FakeFactory:
            def __call__(self):
                return fake

        state_module.AsyncSessionLocal = _FakeFactory()
        try:
            import asyncio

            asyncio.run(run_test())
        finally:
            state_module.AsyncSessionLocal = original

    def test_mark_step_complete_requires_run_id(self) -> None:
        """mark_step_complete should be a no-op when run_id is not set."""
        manager = PipelineStateManager()

        async def run_test():
            await manager.mark_step_complete("ingest")

        import asyncio

        asyncio.run(run_test())

    def test_mark_completed_requires_run_id(self) -> None:
        """mark_completed should be a no-op when run_id is not set."""
        manager = PipelineStateManager()

        async def run_test():
            await manager.mark_completed()

        import asyncio

        asyncio.run(run_test())

    def test_mark_failed_requires_run_id(self) -> None:
        """mark_failed should be a no-op when run_id is not set."""
        manager = PipelineStateManager()

        async def run_test():
            await manager.mark_failed(RuntimeError("boom"), "ingest")

        import asyncio

        asyncio.run(run_test())


class _TransitionSession:
    """In-memory session that applies PipelineRun UPDATE statements."""

    def __init__(self, runs=None):
        self.runs = {run.id: run for run in (runs or [])}
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def get(self, _model, run_id):
        return self.runs.get(run_id)

    def add(self, run):
        if run.id is None:
            run.id = uuid4()
        self.runs[run.id] = run

    async def flush(self):
        return None

    async def commit(self):
        self.commits += 1

    async def execute(self, statement):
        criteria = list(getattr(statement, "_where_criteria", ()))
        targets = list(self.runs.values())
        for criterion in criteria:
            key = getattr(getattr(criterion, "left", None), "key", None)
            value = getattr(getattr(criterion, "right", None), "value", None)
            if key == "id":
                targets = [run for run in targets if run.id == value]
            elif key == "status":
                targets = [run for run in targets if run.status == value]

        values = {column.key: bind.value for column, bind in getattr(statement, "_values", {}).items()}
        for run in targets:
            for key, value in values.items():
                setattr(run, key, value)

        return SimpleNamespace(
            scalar_one_or_none=lambda: targets[0] if targets else None,
            fetchall=lambda: [(run.id,) for run in targets],
        )


def _persisted_run(*, status=PipelineRunStatus.running, step_completed=None, results=None):
    return SimpleNamespace(
        id=uuid4(),
        status=status,
        step_completed=step_completed,
        results=results,
        error_message=None,
        error_step=None,
        completed_at=None,
        started_at=None,
    )


@pytest.mark.asyncio
async def test_state_new_run_to_completed_transition() -> None:
    session = _TransitionSession()
    manager = PipelineStateManager()
    manager._session = session

    run_id = await manager.start_run()
    await manager.mark_step_complete("ingest", {"jobs_fetched": 12})
    await manager.mark_completed({"jobs_fetched": 12})

    run = session.runs[run_id]
    assert run.status == PipelineRunStatus.completed
    assert json.loads(run.results) == {"jobs_fetched": 12}
    assert run.completed_at is not None


@pytest.mark.asyncio
async def test_state_new_run_to_failed_transition() -> None:
    session = _TransitionSession()
    manager = PipelineStateManager()
    manager._session = session

    run_id = await manager.start_run()
    await manager.mark_failed(RuntimeError("ingest failed"), "ingest")

    run = session.runs[run_id]
    assert run.status == PipelineRunStatus.failed
    assert run.error_message == "ingest failed"
    assert run.error_step == "ingest"


@pytest.mark.asyncio
async def test_state_resume_failed_run_to_completed_transition() -> None:
    run = _persisted_run(
        status=PipelineRunStatus.failed,
        step_completed="ingest",
    )
    run.error_message = "old failure"
    run.error_step = "ingest"
    session = _TransitionSession([run])
    manager = PipelineStateManager(run.id)
    manager._session = session

    assert await manager.start_run() == run.id
    assert run.status == PipelineRunStatus.running
    assert run.error_message is None
    assert run.error_step is None

    await manager.mark_completed({"resumed": True})
    assert run.status == PipelineRunStatus.completed
    assert json.loads(run.results) == {"resumed": True}


@pytest.mark.asyncio
async def test_state_resume_failed_run_can_fail_at_different_step() -> None:
    run = _persisted_run(
        status=PipelineRunStatus.failed,
        step_completed="ingest",
    )
    session = _TransitionSession([run])
    manager = PipelineStateManager(run.id)
    manager._session = session

    await manager.start_run()
    await manager.mark_failed(RuntimeError("classifier failed"), "classify")

    assert run.status == PipelineRunStatus.failed
    assert run.error_step == "classify"
    assert run.error_message == "classifier failed"


@pytest.mark.asyncio
async def test_state_step_results_merge_with_persisted_results() -> None:
    run = _persisted_run(results=json.dumps({"jobs_fetched": 10}))
    session = _TransitionSession([run])
    manager = PipelineStateManager(run.id)
    manager._session = session

    await manager.mark_step_complete("cleanup", {"locations_cleaned": 4})

    assert run.step_completed == "cleanup"
    assert json.loads(run.results) == {
        "jobs_fetched": 10,
        "locations_cleaned": 4,
    }


@pytest.mark.asyncio
async def test_clear_incomplete_runs_only_fails_running_runs(monkeypatch) -> None:
    import pipeline.runtime.state as state_module

    running = _persisted_run(status=PipelineRunStatus.running)
    failed = _persisted_run(status=PipelineRunStatus.failed)
    session = _TransitionSession([running, failed])
    monkeypatch.setattr(state_module, "AsyncSessionLocal", lambda: session)

    count = await clear_incomplete_runs()

    assert count == 1
    assert running.status == PipelineRunStatus.failed
    assert running.error_message == "Cleared by user"
    assert failed.status == PipelineRunStatus.failed
