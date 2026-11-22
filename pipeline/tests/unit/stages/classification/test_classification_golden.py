"""Golden behavior tests for classification orchestration and error mapping."""

from __future__ import annotations

from pipeline.tests.paths import FIXTURES_DIR
import json
import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from pipeline.stages.classification.llm_client import (
    ClassificationClient,
    ClassificationError,
    RateLimitError,
)
from pipeline.stages.classification.mapping import get_canonical_category
from pipeline.stages.classification.classifier import JobClassifier

FIXTURE_PATH = FIXTURES_DIR / "classification_golden_cases.json"


def _load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _generate_fixture(path: Path = FIXTURE_PATH) -> None:
    """Rewrite the checked-in fixture explicitly after intentional changes."""
    fixture = _load_fixture()
    path.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")


def _category_for_title(title: str) -> str | None:
    lowered = title.lower()
    for token, category in (
        ("software", "software_engineering"),
        ("finance", "finance"),
        ("sales", "sales"),
        ("designer", "product_design"),
        ("recruit", "recruiting"),
        ("data scientist", "data_science"),
    ):
        if token in lowered:
            return category
    return None


class _GoldenClient:
    def __init__(self, case: dict[str, Any]) -> None:
        self.batch_size = case["batch_size"]
        self.max_concurrent = 2
        self.batch_behavior = case.get("batch_behavior", "normal")
        self.batch_calls: list[list[tuple[str, str]]] = []

    async def classify_prompt_batch_with_reasons(
        self, jobs: list[tuple[str, str]]
    ) -> list[tuple[str | None, str, str]]:
        self.batch_calls.append(jobs)
        if self.batch_behavior == "invalid_json":
            return [(None, "invalid_json", "not json")] * len(jobs)
        if self.batch_behavior == "permanent_error":
            raise ClassificationError("permanent", retryable=False)
        if self.batch_behavior == "all_none":
            return [(None, "no_mappable_token", "unknown")] * len(jobs)
        return [
            (category, "ok" if category else "no_mappable_token", category or "unknown")
            for title, _description in jobs
            if (category := _category_for_title(title)) is not None
        ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    _load_fixture()["batch_cases"],
    ids=lambda case: case["name"],
)
async def test_classification_batch_golden(
    case: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    jobs = [(title, "x" * 800 if description == "__LONG__" else description) for title, description in case["jobs"]]
    classifier = JobClassifier.__new__(JobClassifier)
    client = _GoldenClient(case)
    classifier._client = client

    individual_calls: list[tuple[str, str]] = []

    async def classify_one(title: str, description: str) -> tuple[str | None, str, str]:
        individual_calls.append((title, description))
        category = _category_for_title(title)
        return category, "ok" if category else "no_mappable_token", category or "unknown"

    monkeypatch.setattr(classifier, "_classify_job_with_reason", classify_one)

    result = await classifier.classify_batch_with_reasons(jobs)

    assert [list(item) for item in result] == case["expected"]
    if len(jobs) == 1:
        assert individual_calls == jobs
        assert client.batch_calls == []
    if case.get("batch_behavior") in {"invalid_json", "permanent_error"}:
        assert individual_calls == jobs
    if case["name"] == "long_descriptions":
        assert all(len(description) > 500 for _title, description in client.batch_calls[0])


@pytest.mark.parametrize(
    ("raw", "expected"),
    _load_fixture()["mapping_cases"],
)
def test_category_mapping_golden(
    raw: str, expected: str | None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert get_canonical_category(raw) == expected
    if raw == "brand_new_unknown_category":
        assert json.loads((tmp_path / "unmapped_categories.json").read_text()) == ["brand_new_unknown_category"]


@pytest.mark.parametrize(
    ("status", "error_name", "retryable"),
    _load_fixture()["http_status_cases"],
)
def test_http_status_mapping_golden(status: int, error_name: str, retryable: bool) -> None:
    settings = SimpleNamespace(
        resolved_classification_model="model",
        openai_classification_url=None,
        openai_base_url="http://localhost:8080/v1",
        classification_timeout_seconds=1,
        classification_max_concurrent=1,
        classification_batch_size=2,
        classification_temperature=0.0,
        classification_openai_max_tokens=64,
        classification_openai_batch_min_tokens=256,
        classification_openai_batch_tokens_per_job=48,
        classification_parse_retry_attempts=0,
    )
    client = ClassificationClient(settings=settings)
    request = httpx.Request("POST", "http://localhost/classify")
    response = httpx.Response(
        status,
        request=request,
        headers={"retry-after": "2"} if status == 429 else {},
        text="failure",
    )
    error = httpx.HTTPStatusError("failure", request=request, response=response)

    expected_type = RateLimitError if error_name == "RateLimitError" else ClassificationError
    with pytest.raises(expected_type) as raised:
        client._handle_http_error(error, "Role")

    assert raised.value.retryable is retryable


@pytest.mark.asyncio
async def test_rate_limit_is_retried_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = SimpleNamespace(
        resolved_classification_model="model",
        openai_classification_url=None,
        openai_base_url="http://localhost:8080/v1",
        classification_timeout_seconds=1,
        classification_max_concurrent=1,
        classification_batch_size=2,
        classification_temperature=0.0,
        classification_openai_max_tokens=64,
        classification_openai_batch_min_tokens=256,
        classification_openai_batch_tokens_per_job=48,
        classification_parse_retry_attempts=0,
    )
    client = ClassificationClient(settings=settings)
    attempts = 0

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"choices": [{"message": {"content": "software_engineering"}}]}

    class _Client:
        async def post(self, _url: str, json: dict[str, Any]) -> _Response:
            nonlocal attempts
            del json
            attempts += 1
            if attempts == 1:
                raise RateLimitError("limited")
            return _Response()

    async def no_sleep(_delay: float) -> None:
        return None

    def get_client() -> _Client:
        return _Client()

    monkeypatch.setattr(asyncio, "sleep", no_sleep)
    monkeypatch.setattr(client, "_get_client", get_client)

    assert await client._classify_openai_compatible("Role", "Description") == (
        "software_engineering",
        "ok",
        "software_engineering",
    )
    assert attempts == 2


def test_fixture_schema() -> None:
    fixture = _load_fixture()
    assert fixture["version"] == 1
    assert len(fixture["batch_cases"]) >= 10
    assert len(fixture["mapping_cases"]) >= 20
    assert [case[0] for case in fixture["http_status_cases"]] == [
        400,
        401,
        404,
        429,
        500,
        502,
        503,
    ]
