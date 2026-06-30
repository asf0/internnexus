from __future__ import annotations

import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.cli import run_pipeline
from pipeline.ingest.result import IngestResult
from pipeline.runtime.runner import SyncSafetyAssessment


def _ingest_result(total: int = 0, *, complete: bool = True) -> IngestResult:
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


async def _unsafe_assessment(*_args, **_kwargs) -> SyncSafetyAssessment:
    return SyncSafetyAssessment(
        safe=False,
        reasons=("test unsafe sync",),
        stale_count=33_971,
        source_counts={"greenhouse": 582, "lever": 0, "ashby": 0},
        previous_source_counts=None,
    )


class _FakeSort:
    def __init__(self, name: str):
        self.name = name

    def nulls_last(self):
        return self


class _FakeEqPredicate:
    def __init__(self, column, value):
        self.column = column
        self.value = value


class _FakeColumn:
    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other):
        return _FakeEqPredicate(self.name, other)

    def is_(self, _value):
        return self

    def __le__(self, _other):
        return self

    def desc(self):
        return _FakeSort(self.name)

    def asc(self):
        return _FakeSort(self.name)

    def notin_(self, values):
        return _FakeNotInPredicate(values)


class _FakeNotInPredicate:
    def __init__(self, values):
        self.values = set(values)


class _FakeJobModel:
    job_category = _FakeColumn("job_category")
    classification_next_retry_at = _FakeColumn("classification_next_retry_at")
    classification_attempts = _FakeColumn("classification_attempts")
    posted_at = _FakeColumn("posted_at")
    id = _FakeColumn("id")
    title = _FakeColumn("title")
    description_text = _FakeColumn("description_text")


class _FakeQuery:
    def __init__(self, kind: str):
        self.kind = kind
        self.limit_value: int | None = None
        self.excluded_ids: set | None = None

    def select_from(self, _obj):
        return self

    def where(self, *_args):
        for arg in _args:
            if isinstance(arg, _FakeNotInPredicate):
                self.excluded_ids = set(arg.values)
        return self

    def order_by(self, *_args):
        return self

    def limit(self, value: int):
        self.limit_value = value
        return self


class _FakeResult:
    def __init__(self, scalar_value=None, items=None):
        self._scalar_value = scalar_value
        self._items = items or []

    def scalar(self):
        return self._scalar_value

    def scalars(self):
        return self

    def all(self):
        return list(self._items)


class _FakeUpdate:
    def __init__(self, model):
        self.model = model
        self.update_values = {}
        self.job_id = None

    def where(self, *_args):
        for arg in _args:
            if isinstance(arg, _FakeEqPredicate) and arg.column == "id":
                self.job_id = arg.value
        return self

    def values(self, **kwargs):
        self.update_values.update(kwargs)
        return self


class _FakeSession:
    def __init__(self, jobs):
        self.jobs = jobs
        self.commit_calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, _exc_type, _exc, _tb):
        return None

    async def execute(self, query):
        if isinstance(query, _FakeUpdate):
            for job in self.jobs:
                if getattr(job, "id", None) == query.job_id:
                    for key, value in query.update_values.items():
                        setattr(job, key, value)
                    break
            return _FakeResult()

        if query.kind == "count":
            remaining = sum(1 for job in self.jobs if job.job_category is None)
            return _FakeResult(scalar_value=remaining)

        remaining_jobs = [job for job in self.jobs if job.job_category is None]
        if query.excluded_ids:
            remaining_jobs = [job for job in remaining_jobs if getattr(job, "id", None) not in query.excluded_ids]
        take = query.limit_value if query.limit_value is not None else len(remaining_jobs)
        return _FakeResult(items=remaining_jobs[:take])

    async def commit(self):
        self.commit_calls += 1

    def expunge_all(self):
        pass


@pytest.mark.asyncio
async def test_step_classify_requeries_batches_after_each_commit(monkeypatch):
    jobs = [
        SimpleNamespace(id=1, title="A", description_text="d1", job_category=None, classification_attempts=0),
        SimpleNamespace(id=2, title="B", description_text="d2", job_category=None, classification_attempts=0),
        SimpleNamespace(id=3, title="C", description_text="d3", job_category=None, classification_attempts=0),
        SimpleNamespace(id=4, title="D", description_text="d4", job_category=None, classification_attempts=0),
        SimpleNamespace(id=5, title="E", description_text="d5", job_category=None, classification_attempts=0),
    ]
    fake_session = _FakeSession(jobs)

    class _FakeClassifier:
        async def classify_batch(self, inputs):
            categories: list[str | None] = ["software_engineering"] * len(inputs)
            if inputs and inputs[0][0] == "E":
                categories[0] = None
            return categories

        async def classify_batch_with_reasons(self, inputs):
            categories = await self.classify_batch(inputs)
            return [(category, "ok" if category else "no_mappable_token") for category in categories]

    def fake_select(*targets):
        return _FakeQuery("count" if targets and targets[0] is _FAKE_COUNT else "jobs")

    _FAKE_COUNT = object()
    monkeypatch.setattr(run_pipeline, "CLASSIFY_COMMIT_BATCH_SIZE", 2)
    monkeypatch.setattr(
        "pipeline.repositories.sqlalchemy_repo.AsyncSessionLocal",
        lambda: fake_session,
    )
    monkeypatch.setattr("pipeline.repositories.sqlalchemy_repo.Job", _FakeJobModel)
    monkeypatch.setattr("sqlalchemy.select", fake_select)
    monkeypatch.setattr("sqlalchemy.func", SimpleNamespace(count=lambda: _FAKE_COUNT))
    monkeypatch.setattr("sqlalchemy.or_", lambda *args: args[0] if args else None)
    monkeypatch.setattr("sqlalchemy.update", lambda model: _FakeUpdate(model))

    def _get_classifier():
        return _FakeClassifier()

    monkeypatch.setattr("pipeline.classification.get_classifier", _get_classifier)
    monkeypatch.setattr("pipeline.classification.reset_classifier", lambda: None)

    runner = run_pipeline.PipelineRunner()
    success, errors = await runner.step_classify(state=None)

    assert success == 4
    assert errors == 1
    assert fake_session.commit_calls == 3


@pytest.mark.asyncio
async def test_step_classify_does_not_starve_new_rows_when_first_row_fails(monkeypatch):
    jobs = [
        SimpleNamespace(id=1, title="Failing", description_text="d1", job_category=None),
        SimpleNamespace(id=2, title="Second", description_text="d2", job_category=None),
    ]
    fake_session = _FakeSession(jobs)

    class _FakeClassifier:
        async def classify_batch_with_reasons(self, inputs):
            results = []
            for title, _description in inputs:
                if title == "Failing":
                    results.append((None, "no_mappable_token"))
                else:
                    results.append(("software_engineering", "ok"))
            return results

    def fake_select(*targets):
        return _FakeQuery("count" if targets[0] is _FAKE_COUNT else "jobs")

    _FAKE_COUNT = object()
    monkeypatch.setattr(run_pipeline, "CLASSIFY_COMMIT_BATCH_SIZE", 1)
    monkeypatch.setattr(
        "pipeline.repositories.sqlalchemy_repo.AsyncSessionLocal",
        lambda: fake_session,
    )
    monkeypatch.setattr("pipeline.repositories.sqlalchemy_repo.Job", _FakeJobModel)
    monkeypatch.setattr("sqlalchemy.select", fake_select)
    monkeypatch.setattr("sqlalchemy.func", SimpleNamespace(count=lambda: _FAKE_COUNT))

    monkeypatch.setattr("pipeline.classification.get_classifier", lambda: _FakeClassifier())
    monkeypatch.setattr("pipeline.classification.reset_classifier", lambda: None)
    monkeypatch.setattr("sqlalchemy.update", lambda model: _FakeUpdate(model))

    runner = run_pipeline.PipelineRunner()
    success, errors = await runner.step_classify(state=None)

    assert success == 1
    assert errors == 1
    assert jobs[1].job_category == "software_engineering"


@pytest.mark.asyncio
async def test_run_marks_failed_with_current_step(monkeypatch):
    class _FakeState:
        def __init__(self, _run_id=None):
            self.failed_step = None

        async def __aenter__(self):
            return self

        async def __aexit__(self, _exc_type, _exc, _tb):
            return None

        async def start_run(self):
            return "run-1"

        async def mark_completed(self, _results=None):
            return None

        async def mark_failed(self, _error: Exception, step: str):
            self.failed_step = step

        async def mark_step_complete(self, _step: str):
            return None

        def get_resume_step(self, _run):
            return None

    fake_state = _FakeState()

    async def _no_incomplete_run():
        return None

    async def _ok(*_args, **_kwargs):
        return 0

    async def _ingest(*_args, **_kwargs):
        return _ingest_result()

    async def _finalize(*_args, **_kwargs):
        return 0, 0

    async def _classify_fail(*_args, **_kwargs):
        raise RuntimeError("boom")

    runner = run_pipeline.PipelineRunner(
        state_manager_class=lambda run_id=None: fake_state,
        get_incomplete_run_func=_no_incomplete_run,
    )
    runner.step_discover = _ok
    runner.step_sync_inactive = _ok
    runner.step_ingest = _ingest
    runner.finalize_sync = _finalize
    runner.step_mark_stale_jobs = _ok
    runner.step_delete_inactive = _ok
    runner.step_cleanup = _ok
    runner.step_classify = _classify_fail
    runner.step_embed = _ok

    with pytest.raises(RuntimeError, match="boom"):
        await runner.run()

    assert fake_state.failed_step == "classify"


@pytest.mark.asyncio
async def test_run_auto_resumes_from_incomplete_db_run(monkeypatch):
    executed_steps = []
    run_id_args = []

    class _FakeState:
        def __init__(self, run_id=None):
            run_id_args.append(run_id)
            self.run_id = run_id or "new-run"

        async def __aenter__(self):
            return self

        async def __aexit__(self, _exc_type, _exc, _tb):
            return None

        async def start_run(self):
            return self.run_id

        async def mark_completed(self, _results=None):
            return None

        async def mark_failed(self, _error: Exception, _step: str):
            return None

        async def mark_step_complete(self, _step: str):
            return None

        def get_resume_step(self, run):
            steps = run_pipeline.STEPS
            if not run.step_completed:
                return steps[0]
            idx = steps.index(run.step_completed)
            return steps[idx + 1] if idx < len(steps) - 1 else None

    async def _get_incomplete_run():
        return SimpleNamespace(id="run-123", step_completed="cleanup", started_at="now")

    async def _step(name, returns=None):
        executed_steps.append(name)
        return returns if returns is not None else 0

    async def _ingest(*_args, **_kwargs):
        executed_steps.append("ingest")
        return _ingest_result()

    runner = run_pipeline.PipelineRunner(
        state_manager_class=_FakeState,
        get_incomplete_run_func=_get_incomplete_run,
    )
    runner.step_discover = lambda *_a, **_k: _step("discover")
    runner.step_sync_inactive = lambda *_a, **_k: _step("sync_inactive")
    runner.step_ingest = _ingest
    runner.step_delete_inactive = lambda *_a, **_k: _step("delete_inactive")
    runner.step_cleanup = lambda *_a, **_k: _step("cleanup")
    runner.step_classify = lambda *_a, **_k: _step("classify", (0, 0))
    runner.step_embed = lambda *_a, **_k: _step("embed", (0, 0))

    await runner.run()

    assert executed_steps == ["classify", "embed"]
    assert run_id_args == ["run-123"]


@pytest.mark.asyncio
async def test_run_resumes_post_ingest_with_persisted_sync_context(monkeypatch):
    sync_id = uuid4()
    persisted = IngestResult(
        sync_id=sync_id,
        total_fetched=270_000,
        source_counts={"greenhouse": 90_000, "lever": 90_000, "ashby": 90_000},
        fetch_error_counts={"greenhouse": 0, "lever": 0, "ashby": 0},
        source_complete={"greenhouse": True, "lever": True, "ashby": True},
        jobs_changed=123,
    )
    finalized = []

    class _FakeState:
        def __init__(self, run_id=None):
            assert run_id == sync_id
            self.run_id = run_id

        async def __aenter__(self):
            return self

        async def __aexit__(self, _exc_type, _exc, _tb):
            return None

        async def start_run(self):
            return self.run_id

        async def mark_completed(self, _results=None):
            return None

        async def mark_failed(self, _error: Exception, _step: str):
            return None

        async def mark_step_complete(self, _step: str, _results=None):
            return None

    async def _get_incomplete_run():
        raise AssertionError("explicit resume must look up the requested failed run")

    async def _get_resumable_run(requested_run_id):
        assert requested_run_id == sync_id
        return SimpleNamespace(
            id=sync_id,
            step_completed="ingest",
            results=json.dumps(persisted.to_metadata()),
        )

    @asynccontextmanager
    async def _no_lock():
        yield

    async def _unexpected_ingest(*_args, **_kwargs):
        raise AssertionError("resume after ingest must not fetch jobs again")

    async def _finalize(_state, ingest):
        finalized.append(ingest)
        return 5, 5

    async def _zero(*_args, **_kwargs):
        return 0

    async def _zero_pair(*_args, **_kwargs):
        return 0, 0

    monkeypatch.setattr("pipeline.runtime.runner.job_sync_lock", _no_lock)
    runner = run_pipeline.PipelineRunner(
        resume_run_id=sync_id,
        state_manager_class=_FakeState,
        get_incomplete_run_func=_get_incomplete_run,
        get_resumable_run_func=_get_resumable_run,
    )
    runner.step_ingest = _unexpected_ingest
    runner.finalize_sync = _finalize
    runner.step_cleanup = _zero
    runner.step_classify = _zero_pair
    runner.step_embed = _zero_pair

    results = await runner.run()

    assert finalized == [persisted]
    assert results["sync_id"] == str(sync_id)
    assert results["jobs_fetched"] == 270_000
    assert results["jobs_marked_inactive"] == 5
    assert results["inactive_jobs_deleted"] == 5


@pytest.mark.asyncio
async def test_run_resume_step_does_not_persist_across_runs(monkeypatch):
    run_id_args = []
    executed_runs = []
    current_steps = []

    class _FakeState:
        def __init__(self, run_id=None):
            run_id_args.append(run_id)
            self.run_id = run_id or "new-run"

        async def __aenter__(self):
            return self

        async def __aexit__(self, _exc_type, _exc, _tb):
            return None

        async def start_run(self):
            return self.run_id

        async def mark_completed(self, _results=None):
            return None

        async def mark_failed(self, _error: Exception, _step: str):
            return None

        async def mark_step_complete(self, _step: str):
            return None

        def get_resume_step(self, run):
            steps = run_pipeline.STEPS
            if not run.step_completed:
                return steps[0]
            idx = steps.index(run.step_completed)
            return steps[idx + 1] if idx < len(steps) - 1 else None

    incomplete_runs = [
        SimpleNamespace(id="run-123", step_completed="cleanup", started_at="now"),
        None,
    ]

    async def _get_incomplete_run():
        return incomplete_runs.pop(0)

    def _record(name):
        async def _inner(*_args, **_kwargs):
            current_steps.append(name)
            if name == "ingest":
                return _ingest_result()
            if name in {"classify", "embed"}:
                return 0, 0
            return 0

        return _inner

    runner = run_pipeline.PipelineRunner(
        state_manager_class=_FakeState,
        get_incomplete_run_func=_get_incomplete_run,
    )
    runner.step_discover = _record("discover")
    runner.step_sync_inactive = _record("sync_inactive")
    runner.step_ingest = _record("ingest")
    runner.step_mark_stale_jobs = _record("mark_stale_jobs")
    runner.step_delete_inactive = _record("delete_inactive")
    runner.step_cleanup = _record("cleanup")
    runner.step_classify = _record("classify")
    runner.step_embed = _record("embed")

    async def _finalize(*_args, **_kwargs):
        current_steps.extend(["mark_stale_jobs", "delete_inactive"])
        return 0, 0

    runner.finalize_sync = _finalize

    await runner.run()
    executed_runs.append(list(current_steps))
    current_steps.clear()

    await runner.run()
    executed_runs.append(list(current_steps))

    assert executed_runs[0] == ["classify", "embed"]
    assert executed_runs[1] == [
        "discover",
        "sync_inactive",
        "ingest",
        "mark_stale_jobs",
        "delete_inactive",
        "cleanup",
        "classify",
        "embed",
    ]
    assert run_id_args == ["run-123", None]


@pytest.mark.asyncio
async def test_run_rejects_suspicious_ingest_before_any_stale_mutation(monkeypatch):
    completed_steps = []
    called_delete = False
    called_rollback = False

    class _FakeState:
        def __init__(self, run_id=None):
            self.run_id = run_id or "run-1"

        async def __aenter__(self):
            return self

        async def __aexit__(self, _exc_type, _exc, _tb):
            return None

        async def start_run(self):
            return self.run_id

        async def mark_completed(self, _results=None):
            return None

        async def mark_failed(self, _error: Exception, _step: str):
            return None

        async def mark_step_complete(self, step: str, _results=None):
            completed_steps.append(step)

    async def _get_incomplete_run():
        return None

    async def _discover(*_args, **_kwargs):
        return 0

    async def _sync_inactive(*_args, **_kwargs):
        return 33971

    async def _ingest(*_args, **_kwargs):
        return _ingest_result(582)

    async def _delete(*_args, **_kwargs):
        nonlocal called_delete
        called_delete = True
        return 33391

    async def _rollback(*_args, **_kwargs):
        nonlocal called_rollback
        called_rollback = True
        return 33391

    async def _zero(*_args, **_kwargs):
        return 0

    async def _zero_pair(*_args, **_kwargs):
        return 0, 0

    runner = run_pipeline.PipelineRunner(
        state_manager_class=_FakeState,
        get_incomplete_run_func=_get_incomplete_run,
    )
    runner.step_discover = _discover
    runner.step_sync_inactive = _sync_inactive
    runner.step_ingest = _ingest
    runner.step_mark_stale_jobs = _sync_inactive
    runner.step_delete_inactive = _delete
    runner.assess_sync = _unsafe_assessment
    runner.cleanup_sync_sightings = _zero
    runner.step_cleanup = _zero
    runner.step_classify = _zero_pair
    runner.step_embed = _zero_pair

    results = await runner.run()

    assert called_delete is False
    assert called_rollback is False
    assert results["inactive_jobs_deleted"] == 0
    assert "delete_inactive" in completed_steps


@pytest.mark.asyncio
async def test_run_skips_delete_when_resuming_after_sync_inactive(monkeypatch):
    called_delete = False
    called_rollback = False

    class _FakeState:
        def __init__(self, run_id=None):
            self.run_id = run_id or "run-1"

        async def __aenter__(self):
            return self

        async def __aexit__(self, _exc_type, _exc, _tb):
            return None

        async def start_run(self):
            return self.run_id

        async def mark_completed(self, _results=None):
            return None

        async def mark_failed(self, _error: Exception, _step: str):
            return None

        async def mark_step_complete(self, _step: str, _results=None):
            return None

    async def _get_incomplete_run():
        return SimpleNamespace(id="run-123", step_completed="sync_inactive", started_at="now")

    async def _ingest(*_args, **_kwargs):
        return _ingest_result(30000)

    async def _delete(*_args, **_kwargs):
        nonlocal called_delete
        called_delete = True
        return 1

    async def _rollback(*_args, **_kwargs):
        nonlocal called_rollback
        called_rollback = True
        return 1

    async def _zero(*_args, **_kwargs):
        return 0

    async def _zero_pair(*_args, **_kwargs):
        return 0, 0

    runner = run_pipeline.PipelineRunner(
        state_manager_class=_FakeState,
        get_incomplete_run_func=_get_incomplete_run,
    )
    runner.step_ingest = _ingest
    runner.step_mark_stale_jobs = _zero
    runner.step_delete_inactive = _delete
    runner.assess_sync = _unsafe_assessment
    runner.cleanup_sync_sightings = _zero
    runner.step_cleanup = _zero
    runner.step_classify = _zero_pair
    runner.step_embed = _zero_pair

    results = await runner.run()

    assert called_delete is False
    assert called_rollback is False
    assert results["inactive_jobs_deleted"] == 0


def test_delete_inactive_guard_allows_small_syncs():
    from pipeline.runtime.runner import _is_unsafe_delete_inactive_sync

    assert _is_unsafe_delete_inactive_sync(50, 1) is False
    assert _is_unsafe_delete_inactive_sync(33971, 582) is True
    assert _is_unsafe_delete_inactive_sync(33971, 30000) is False


@pytest.mark.asyncio
async def test_cli_runner_uses_dependency_injection_without_monkeypatch():
    """The CLI runner must use constructor-injected dependencies, not mutate runner globals."""
    from pipeline.runtime import runner as runner_module

    original_state_manager = runner_module.PipelineStateManager
    original_get_incomplete_run = runner_module.get_incomplete_run

    state_calls = []

    class _FakeState:
        def __init__(self, run_id=None):
            state_calls.append(run_id)
            self.run_id = run_id or "fake-run"

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def start_run(self):
            return self.run_id

        async def mark_completed(self, _results=None):
            return None

        async def mark_failed(self, _error, _step):
            return None

        async def mark_step_complete(self, _step):
            return None

    async def _get_incomplete_run():
        return None

    async def _zero(*_args, **_kwargs):
        return 0

    async def _zero_pair(*_args, **_kwargs):
        return 0, 0

    async def _ingest(*_args, **_kwargs):
        return _ingest_result()

    async def _finalize(*_args, **_kwargs):
        return 0, 0

    runner = run_pipeline.PipelineRunner(
        state_manager_class=_FakeState,
        get_incomplete_run_func=_get_incomplete_run,
    )
    runner.step_discover = _zero
    runner.step_sync_inactive = _zero
    runner.step_ingest = _ingest
    runner.finalize_sync = _finalize
    runner.step_mark_stale_jobs = _zero
    runner.step_delete_inactive = _zero
    runner.step_cleanup = _zero
    runner.step_classify = _zero_pair
    runner.step_embed = _zero_pair

    await runner.run()

    assert state_calls == [None]
    assert runner_module.PipelineStateManager is original_state_manager
    assert runner_module.get_incomplete_run is original_get_incomplete_run
