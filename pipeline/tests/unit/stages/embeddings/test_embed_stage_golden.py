"""Golden behavior tests for embedding pipeline counts and error classification."""

from __future__ import annotations

from pipeline.tests.paths import FIXTURES_DIR
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from internnexus_core.embedding import EmbeddingError, RateLimitError

from pipeline.stages.embeddings import batch_embedder
from pipeline.stages.embeddings import embed_stage
from pipeline.stages.embeddings import retry_handler
from pipeline.stages.embeddings.batch_embedder import _classify_error

FIXTURE_PATH = FIXTURES_DIR / "embedding_pipeline_golden_cases.json"


def _load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _generate_fixture(path: Path = FIXTURE_PATH) -> None:
    """Rewrite the checked-in fixture explicitly after intentional changes."""
    fixture = _load_fixture()
    path.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    _load_fixture()["cases"],
    ids=lambda case: case["name"],
)
async def test_embedding_pipeline_counts_golden(case: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    retry_queue_size = case.get("retry_queue_size", 0)
    retry_queue = [(uuid4(), "embedding_error", "temporary", 0) for _ in range(retry_queue_size)]
    observed: dict[str, int] = {"retried": 0, "parallelism": 0}
    remaining = iter([case["initial_count"], 0])

    async def get_remaining(_db: object) -> int:
        return next(remaining, 0)

    async def process_batches(
        _db: object,
        semaphore: asyncio.Semaphore,
        _embedder: object,
        _batch_size: int,
        _parallel_batches: int,
    ) -> tuple[int, int, int, list, bool]:
        observed["parallelism"] = semaphore._value
        success, errors, skipped = case["batch_result"]
        return success, errors, skipped, list(retry_queue), False

    async def process_retries(*_args: object, **_kwargs: object) -> tuple[int, int, int, list]:
        observed["retried"] = retry_queue_size
        success, errors, skipped = case["retry_result"]
        return success, errors, skipped, []

    async def log_final_stats(_db: object, success: int, errors: int, skipped: int) -> None:
        observed["final_success"] = success
        observed["final_errors"] = errors
        observed["final_skipped"] = skipped

    monkeypatch.setattr(embed_stage, "_get_remaining_count", get_remaining)
    monkeypatch.setattr(embed_stage, "_process_batches", process_batches)
    monkeypatch.setattr(embed_stage, "_process_retry_queue", process_retries)
    monkeypatch.setattr(embed_stage, "_log_final_stats", log_final_stats)

    success, errors = await embed_stage._run_embedding_pipeline(object(), object(), batch_size=3, parallel_batches=2)

    expected = case["expected"]
    assert success == expected["success"]
    assert errors == expected["errors"]
    assert observed["retried"] == expected["retried"]
    assert observed.get("final_skipped", 0) == expected["skipped"]
    if case["initial_count"]:
        assert observed["parallelism"] == 2


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (RateLimitError("limited"), ("rate_limit", True)),
        (EmbeddingError("retry", retryable=True), ("embedding_error", True)),
        (EmbeddingError("permanent"), ("embedding_error", False)),
        (asyncio.TimeoutError(), ("timeout", True)),
        (TimeoutError(), ("timeout", True)),
        (asyncio.CancelledError(), ("cancelled", False)),
        (RuntimeError("unknown"), ("unknown", True)),
        (ValueError("unknown"), ("unknown", True)),
        (OSError("unknown"), ("unknown", True)),
        (Exception("unknown"), ("unknown", True)),
    ],
)
def test_embedding_error_classification_golden(error: BaseException, expected: tuple[str, bool]) -> None:
    assert _classify_error(error) == expected


def test_fixture_schema() -> None:
    fixture = _load_fixture()
    assert fixture["version"] == 1
    assert len(fixture["cases"]) == 7
    for case in fixture["cases"]:
        assert set(case["expected"]) == {"success", "errors", "skipped", "retried"}


def test_empty_and_short_jobs_are_skipped_and_logged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        batch_embedder,
        "get_config",
        lambda: SimpleNamespace(
            logging=SimpleNamespace(logs_dir=tmp_path),
            embeddings=SimpleNamespace(api_batch_size=16),
        ),
    )
    jobs = [
        SimpleNamespace(
            id=uuid4(),
            description_text="",
            company="Acme",
            title="Empty",
            apply_url="https://example.com/empty",
        ),
        SimpleNamespace(
            id=uuid4(),
            description_text="short",
            company="Acme",
            title="Short",
            apply_url="https://example.com/short",
        ),
        SimpleNamespace(
            id=uuid4(),
            description_text="A sufficiently detailed role description for embedding.",
            company="Acme",
            title="Valid",
            apply_url="https://example.com/valid",
        ),
    ]

    valid_jobs, texts, skipped = batch_embedder._prepare_job_texts(jobs)

    assert valid_jobs == [jobs[2]]
    assert len(texts) == 1
    assert [reason for _job_id, reason in skipped] == ["empty_text", "too_short"]
    records = [json.loads(line) for line in batch_embedder._get_skipped_jobs_log_path().read_text().splitlines()]
    assert [record["reason"] for record in records] == ["empty_text", "too_short"]


def test_permanent_embedding_error_is_counted_and_logged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        batch_embedder,
        "get_config",
        lambda: SimpleNamespace(
            logging=SimpleNamespace(logs_dir=tmp_path),
            embeddings=SimpleNamespace(api_batch_size=16),
        ),
    )
    job = SimpleNamespace(
        id=uuid4(),
        company="Acme",
        title="Failed",
        apply_url="https://example.com/failed",
    )

    result = batch_embedder._handle_batch_error(
        [job],
        EmbeddingError("invalid response", retryable=False),
        batch_num=1,
        retry_attempt=0,
    )

    assert result == (0, 1, [])
    record = json.loads(batch_embedder._get_failed_jobs_log_path().read_text().strip())
    assert record["error_type"] == "embedding_error"
    assert record["will_retry"] is False


@pytest.mark.asyncio
async def test_retry_queue_succeeds_on_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_id = uuid4()

    async def no_sleep(_delay: float) -> None:
        return None

    async def process(*_args: object, **_kwargs: object) -> tuple[int, int, int, list]:
        return 1, 0, 0, []

    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    monkeypatch.setattr(retry_handler, "_process_with_semaphore", process)

    result = await retry_handler._process_retry_queue(
        [(job_id, "embedding_error", "temporary", 0)],
        embedder=object(),
        db=object(),
        semaphore=asyncio.Semaphore(1),
        batch_size=1,
    )

    assert result == (1, 0, 0, [])


@pytest.mark.asyncio
async def test_exhausted_retry_remains_queued_for_single_final_log(monkeypatch) -> None:
    job_id = uuid4()
    failure = EmbeddingError("still unavailable", retryable=True)
    permanent_logs: list[object] = []

    async def no_sleep(_delay: float) -> None:
        return None

    async def process(*_args: object, **_kwargs: object):
        return 0, 0, 0, [(job_id, failure)]

    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    monkeypatch.setattr(retry_handler, "_process_with_semaphore", process)
    monkeypatch.setattr(retry_handler, "_log_failed_job", lambda *args, **kwargs: permanent_logs.append((args, kwargs)))

    result = await retry_handler._process_retry_queue(
        [(job_id, "embedding_error", "temporary", 0)],
        embedder=object(),
        db=object(),
        semaphore=asyncio.Semaphore(1),
        batch_size=1,
    )

    assert result[:3] == (0, 0, 0)
    assert result[3] == [(job_id, "embedding_error", "still unavailable", 2)]
    assert permanent_logs == []


@pytest.mark.asyncio
async def test_exhausted_retry_is_counted_once_by_pipeline(monkeypatch) -> None:
    job_id = uuid4()
    remaining = [(job_id, "embedding_error", "unavailable", 2)]
    final_log_calls: list[list[tuple]] = []

    async def process_retries(*_args, **_kwargs):
        return 0, 0, 0, remaining

    async def log_exhausted(queue, _db):
        final_log_calls.append(queue)
        return len(queue)

    monkeypatch.setattr(embed_stage, "_process_retry_queue", process_retries)
    monkeypatch.setattr(embed_stage, "_log_exhausted_retries", log_exhausted)

    result = await embed_stage._handle_retries(
        remaining,
        embedder=object(),
        db=object(),
        semaphore=asyncio.Semaphore(1),
        batch_size=1,
        parallel_batches=1,
        total_success=0,
        total_errors=0,
        total_skipped=0,
    )

    assert result == (0, 1, 0)
    assert final_log_calls == [remaining]
