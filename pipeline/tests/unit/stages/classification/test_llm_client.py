"""Targeted provider strategy tests for classification requests."""

from __future__ import annotations

import json as json_module
from types import SimpleNamespace
from typing import Any

import pytest

from pipeline.stages.classification.llm_client import ClassificationClient


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        resolved_classification_model="test-model",
        openai_classification_url=None,
        openai_base_url="http://provider",
        classification_timeout_seconds=1,
        classification_max_concurrent=1,
        classification_batch_size=10,
        classification_temperature=0.0,
        classification_openai_max_tokens=64,
        classification_openai_batch_min_tokens=256,
        classification_openai_batch_tokens_per_job=48,
        classification_parse_retry_attempts=0,
    )


class _Response:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("batch", "response_payload"),
    [
        (
            False,
            {"choices": [{"message": {"content": "software_engineering"}}]},
        ),
        (
            True,
            {
                "choices": [
                    {
                        "message": {
                            "content": json_module.dumps(
                                [
                                    {
                                        "id": "0",
                                        "category": "software_engineering",
                                    },
                                    {"id": "1", "category": "finance"},
                                ]
                            )
                        }
                    }
                ]
            },
        ),
    ],
)
async def test_provider_strategy_single_and_batch_paths(
    batch: bool,
    response_payload: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    class _Client:
        async def post(self, url: str, json: dict[str, Any]) -> _Response:
            calls.append((url, json))
            return _Response(response_payload)

    client = ClassificationClient(settings=_settings())

    def get_client() -> _Client:
        return _Client()

    monkeypatch.setattr(client, "_get_client", get_client)
    jobs = [
        ("Software Engineer", "Build APIs"),
        ("Finance Analyst", "Analyze budgets"),
    ]

    if batch:
        result = await client.classify_prompt_batch_with_reasons(jobs)
        assert [item[0] for item in result] == ["software_engineering", "finance"]
    else:
        result = await client.classify_job_with_reason(*jobs[0])
        assert result[0] == "software_engineering"

    assert len(calls) == 1
    url, body = calls[0]
    assert url == "http://provider/v1/chat/completions"
    assert "max_tokens" in body


@pytest.mark.asyncio
async def test_openai_request_parameters_come_from_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings()
    settings.classification_temperature = 0.25
    settings.classification_openai_max_tokens = 48
    settings.classification_openai_batch_min_tokens = 192
    bodies: list[dict[str, Any]] = []

    class _Client:
        async def post(self, _url: str, json: dict[str, Any]) -> _Response:
            bodies.append(json)
            if len(bodies) == 1:
                return _Response({"choices": [{"message": {"content": "software_engineering"}}]})
            return _Response(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json_module.dumps(
                                    [
                                        {
                                            "id": "0",
                                            "category": "software_engineering",
                                        },
                                        {"id": "1", "category": "finance"},
                                    ]
                                )
                            }
                        }
                    ]
                }
            )

    def get_client() -> _Client:
        return _Client()

    client = ClassificationClient(settings=settings)
    monkeypatch.setattr(client, "_get_client", get_client)

    await client.classify_job_with_reason("Software Engineer", "Build APIs")
    await client.classify_prompt_batch_with_reasons(
        [
            ("Software Engineer", "Build APIs"),
            ("Finance Analyst", "Analyze budgets"),
        ]
    )

    assert bodies[0]["temperature"] == 0.25
    assert bodies[0]["max_tokens"] == 48
    assert bodies[1]["temperature"] == 0.25
    assert bodies[1]["max_tokens"] == 192


@pytest.mark.asyncio
async def test_single_job_retries_on_unparseable_response_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings()
    settings.classification_parse_retry_attempts = 2
    responses = [
        {"choices": [{"message": {"content": "not json at all"}}]},
        {"choices": [{"message": {"content": '{"category":"finance"}'}}]},
    ]

    class _Client:
        async def post(self, _url: str, json: dict[str, Any]) -> _Response:
            return _Response(responses.pop(0))

    def get_client() -> _Client:
        return _Client()

    client = ClassificationClient(settings=settings)
    monkeypatch.setattr(client, "_get_client", get_client)

    category, reason, _raw = await client.classify_job_with_reason("Finance Analyst", "Analyze budgets")

    assert category == "finance"
    assert reason == "ok"
    assert responses == []


@pytest.mark.asyncio
async def test_single_job_gives_up_after_exhausting_parse_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings()
    settings.classification_parse_retry_attempts = 1
    calls = 0

    class _Client:
        async def post(self, _url: str, json: dict[str, Any]) -> _Response:
            nonlocal calls
            calls += 1
            return _Response({"choices": [{"message": {"content": "still not json"}}]})

    def get_client() -> _Client:
        return _Client()

    client = ClassificationClient(settings=settings)
    monkeypatch.setattr(client, "_get_client", get_client)

    category, reason, _raw = await client.classify_job_with_reason("Finance Analyst", "Analyze budgets")

    assert category is None
    assert reason == "no_mappable_token"
    assert calls == 2
