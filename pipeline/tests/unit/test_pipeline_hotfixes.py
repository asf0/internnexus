from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.cli import run_pipeline
from pipeline.embeddings import pipeline as embeddings_pipeline


def _fake_config() -> SimpleNamespace:
    return SimpleNamespace(pipeline=SimpleNamespace(continuous_interval=60))


def test_main_check_exits_non_zero_when_unhealthy(monkeypatch):
    async def _run_health_checks():
        return [SimpleNamespace(name="Database", healthy=False, message="down")]

    monkeypatch.setattr(run_pipeline, "get_config", _fake_config)
    monkeypatch.setattr(run_pipeline, "run_health_checks", _run_health_checks)
    monkeypatch.setattr(run_pipeline, "print_health_report", lambda _results: False)
    monkeypatch.setattr(sys, "argv", ["run_pipeline.py", "--check"])

    with pytest.raises(SystemExit) as exc_info:
        run_pipeline.main()

    assert exc_info.value.code == 1


def test_main_cleanup_step_passes_limit(monkeypatch):
    calls: dict[str, int | None] = {"limit": None, "runner_limit": None}

    class _FakeRunner:
        def __init__(
            self,
            skip_discover: bool = False,
            dry_run: bool = False,
            process_all: bool = False,
            resume_run_id=None,
            test_mode: bool = False,
            limit: int | None = None,
        ):
            calls["runner_limit"] = limit

        async def step_cleanup(self, _state, since=None, test_mode: bool = False, limit: int | None = None):
            calls["limit"] = limit
            return 0

    monkeypatch.setattr(run_pipeline, "get_config", _fake_config)
    monkeypatch.setattr(run_pipeline, "_RuntimePipelineRunner", _FakeRunner)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_pipeline.py", "--step", "cleanup", "--limit", "7", "--skip-check"],
    )

    run_pipeline.main()

    assert calls["runner_limit"] == 7
    assert calls["limit"] == 7


def test_main_continuous_uses_interval_and_runner(monkeypatch):
    calls: dict[str, int | bool | None] = {
        "interval": None,
        "ran_continuous": False,
    }

    class _FakeRunner:
        def __init__(self, **_kwargs):
            return None

    async def _fake_run_continuous(runner, interval):
        assert isinstance(runner, _FakeRunner)
        calls["ran_continuous"] = True
        calls["interval"] = interval

    async def _fake_get_incomplete_run():
        return None

    monkeypatch.setattr(run_pipeline, "get_config", _fake_config)
    monkeypatch.setattr(run_pipeline, "_RuntimePipelineRunner", _FakeRunner)
    monkeypatch.setattr(run_pipeline, "run_continuous", _fake_run_continuous)
    monkeypatch.setattr(run_pipeline, "get_incomplete_run", _fake_get_incomplete_run)
    monkeypatch.setattr(sys, "argv", ["run_pipeline.py", "--continuous", "--interval", "5"])

    run_pipeline.main()

    assert calls["ran_continuous"] is True
    assert calls["interval"] == 5


def test_cli_runner_is_warning_only_compatibility_shim():
    with pytest.warns(DeprecationWarning, match="pipeline.runtime.runner"):
        runner = run_pipeline.PipelineRunner(dry_run=True)

    assert isinstance(runner, run_pipeline._RuntimePipelineRunner)


@pytest.mark.asyncio
async def test_generate_embeddings_honors_injected_session(monkeypatch):
    fake_session = object()
    fake_embedder = object()
    captured: dict[str, object] = {}

    monkeypatch.setattr(embeddings_pipeline, "_initialize_embedder", lambda: fake_embedder)

    async def _fake_run_pipeline(db, embedder, batch_size, parallel_batches):
        captured["db"] = db
        captured["embedder"] = embedder
        captured["batch_size"] = batch_size
        captured["parallel_batches"] = parallel_batches
        return 12, 1

    def _fail_session_local():
        raise AssertionError("AsyncSessionLocal should not be used when session is injected")

    monkeypatch.setattr(embeddings_pipeline, "_run_embedding_pipeline", _fake_run_pipeline)
    monkeypatch.setattr(embeddings_pipeline, "AsyncSessionLocal", _fail_session_local)

    result = await embeddings_pipeline.generate_embeddings(
        session=fake_session,
        batch_size=25,
        parallel_batches=4,
    )

    assert result == (12, 1)
    assert captured["db"] is fake_session
    assert captured["embedder"] is fake_embedder
    assert captured["batch_size"] == 25
    assert captured["parallel_batches"] == 4
