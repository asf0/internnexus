from __future__ import annotations

from pipeline.tests.paths import PROJECT_ROOT
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.cli import run_pipeline
from pipeline.stages.embeddings import embed_stage as embeddings_pipeline
from pipeline.runtime import health
from pipeline.runtime import services
from pipeline.runtime import commands
from pipeline.infra.models import PipelineCommandStatus


def _fake_config() -> SimpleNamespace:
    return SimpleNamespace(pipeline=SimpleNamespace(continuous_interval=60))


def test_main_check_exits_non_zero_when_unhealthy(monkeypatch):
    async def _run_and_report_health():
        return False

    monkeypatch.setattr(run_pipeline, "get_config", _fake_config)
    monkeypatch.setattr(run_pipeline, "run_and_report_health", _run_and_report_health)
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
        "health_checked": False,
    }

    class _FakeRunner:
        def __init__(self, **_kwargs):
            return None

        async def run_health_checks(self):
            calls["health_checked"] = True
            return True

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
    assert calls["health_checked"] is True


def test_cli_parser_rejects_removed_sync_inactive() -> None:
    parser = run_pipeline.build_parser(_fake_config())

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--step", "sync_inactive"])

    assert exc_info.value.code == 2


@pytest.mark.asyncio
async def test_continuous_error_uses_configured_backoff_and_single_cleanup(monkeypatch) -> None:
    sleeps: list[int] = []
    cleanup_calls = 0

    class _Runner:
        config = SimpleNamespace(pipeline=SimpleNamespace(backoff_on_error=7, max_backoff_multiplier=5))
        resume_run_id = None

        async def run(self):
            raise RuntimeError("boom")

    async def sleep(seconds: int):
        sleeps.append(seconds)
        raise KeyboardInterrupt

    async def cleanup():
        nonlocal cleanup_calls
        cleanup_calls += 1

    monkeypatch.setattr(services, "claim_next_pending_command", AsyncMock(return_value=None))
    monkeypatch.setattr(services, "cleanup_resources", cleanup)
    monkeypatch.setattr(services.asyncio, "sleep", sleep)

    with pytest.raises(KeyboardInterrupt):
        await services.run_continuous_loop(
            runner=_Runner(),
            interval=3600,
            get_incomplete_run=AsyncMock(return_value=None),
            logger=SimpleNamespace(
                exception=lambda *_args: None,
                warning=lambda *_args: None,
                info=lambda *_args: None,
            ),
        )

    assert sleeps == [7]
    assert cleanup_calls == 1


@pytest.mark.asyncio
async def test_claim_recovers_expired_running_command_before_claim(monkeypatch) -> None:
    command = SimpleNamespace(
        status=PipelineCommandStatus.pending,
        started_at=None,
        error_message="old crash",
    )
    statements: list[object] = []

    class _Result:
        def scalar_one_or_none(self):
            return command

    class _Session:
        async def execute(self, statement):
            statements.append(statement)
            return _Result()

        async def commit(self):
            return None

        async def refresh(self, _command):
            return None

        def expunge(self, _command):
            return None

    class _SessionContext:
        async def __aenter__(self):
            return _Session()

        async def __aexit__(self, *_args):
            return None

    monkeypatch.setattr(commands, "AsyncSessionLocal", _SessionContext)
    monkeypatch.setattr(
        commands,
        "get_config",
        lambda: SimpleNamespace(pipeline=SimpleNamespace(command_lease_seconds=600)),
    )

    claimed = await commands.claim_next_pending_command()

    assert claimed is command
    assert len(statements) == 2
    recovery_params = statements[0].compile().params
    assert recovery_params["status"] is PipelineCommandStatus.pending
    assert recovery_params["error_message"] == "Recovered after command lease expired"
    assert command.status is PipelineCommandStatus.running
    assert command.started_at is not None
    assert command.error_message is None


@pytest.mark.asyncio
async def test_generate_embeddings_honors_injected_session(monkeypatch):
    fake_session = cast(AsyncSession, object())
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


@pytest.mark.parametrize(
    "argv",
    [
        ["--step", "delete_inactive"],
        ["--check", "--resume"],
        ["--check", "--continuous"],
        ["--resume", "--fresh"],
        ["--delete-inactive"],
    ],
)
def test_cli_parser_rejects_incompatible_modes(argv) -> None:
    parser = run_pipeline.build_parser(_fake_config())

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(argv)

    assert exc_info.value.code == 2


@pytest.mark.asyncio
async def test_health_checks_probe_embedding_and_all_configured_sources(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    class Response:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"embedding": [0.0, 0.0, 0.0]}]}

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, **_kwargs):
            calls.append(("post", url))
            return Response()

        async def get(self, url, **_kwargs):
            calls.append(("get", url))
            return Response()

    settings = SimpleNamespace(
        openai_base_url="http://embed/v1",
        embedding_model="model",
        embedding_dimensions=3,
        greenhouse_api_url="http://greenhouse",
        lever_api_url="http://lever",
        ashby_api_url="http://ashby",
        simplify_jobs_intern_url="http://simplify/intern",
        simplify_jobs_new_grad_url="http://simplify/new-grad",
    )
    config = SimpleNamespace(
        health_check=SimpleNamespace(timeout=1),
        discovery=SimpleNamespace(searxng_url="http://searxng"),
    )
    monkeypatch.setattr(health, "get_settings", lambda: settings)
    monkeypatch.setattr(health, "get_config", lambda: config)
    monkeypatch.setattr(health.httpx, "AsyncClient", lambda **_kwargs: Client())

    embedding = await health.check_embedding_service()
    sources = await health.check_job_apis()

    assert embedding.healthy is True
    assert ("post", "http://embed/v1/embeddings") in calls
    assert sources.healthy is True
    assert set(sources.details) == {
        "greenhouse",
        "lever",
        "ashby",
        "simplify_intern",
        "simplify_new_grad",
    }
