from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from pipeline.stages.classification import classifier as classifier_mod


def test_extract_batch_categories_accepts_json_array_in_input_order():
    raw = json.dumps(
        [
            {"id": "1", "category": "finance"},
            {"id": "0", "category": "software-engineering"},
        ]
    )

    assert classifier_mod._extract_batch_categories(raw, 2) == [
        ("software_engineering", "ok", raw),
        ("finance", "ok", raw),
    ]


def test_extract_batch_categories_accepts_wrapped_results_and_rejects_missing():
    raw = json.dumps({"results": [{"id": "0", "category": "sales"}]})

    assert classifier_mod._extract_batch_categories(raw, 2) == [
        ("sales", "ok", raw),
        (None, "missing_batch_result", raw),
    ]


def test_extract_batch_categories_rejects_invalid_json():
    assert classifier_mod._extract_batch_categories("not json", 2) == [
        (None, "invalid_json", "not json"),
        (None, "invalid_json", "not json"),
    ]


@pytest.mark.asyncio
async def test_openai_compatible_batch_classification_uses_one_request(monkeypatch):
    calls: list[tuple[str, dict[str, object]]] = []

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, list[dict[str, dict[str, str]]]]:
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                [
                                    {"id": "0", "category": "software_engineering"},
                                    {"id": "1", "category": "finance"},
                                    {"id": "2", "category": "sales"},
                                ]
                            )
                        }
                    }
                ]
            }

    class _Client:
        async def post(self, url: str, json: dict[str, object]):
            calls.append((url, json))
            return _Response()

    monkeypatch.setattr(
        classifier_mod,
        "get_settings",
        lambda: SimpleNamespace(
            resolved_classification_model="qwen3.6-35b-a3b:code",
            openai_base_url="http://192.168.0.4:8080",
            openai_classification_url="http://192.168.0.4:8080",
            classification_timeout_seconds=90.0,
            classification_max_concurrent=1,
            classification_batch_size=10,
            classification_temperature=0.0,
            classification_openai_max_tokens=64,
            classification_openai_batch_min_tokens=256,
            classification_openai_batch_tokens_per_job=48,
            classification_parse_retry_attempts=0,
        ),
    )

    classifier = classifier_mod.JobClassifier()

    def _get_client():
        return _Client()

    monkeypatch.setattr(classifier._client, "_get_client", _get_client)

    result = await classifier.classify_batch_with_reasons(
        [
            ("Software Engineer Intern", "Build APIs"),
            ("Finance Analyst", "Analyze budgets"),
            ("Sales Development Representative", "Qualify leads"),
        ]
    )

    assert result == [("software_engineering", "ok"), ("finance", "ok"), ("sales", "ok")]
    assert len(calls) == 1
    url, payload = calls[0]
    assert url == "http://192.168.0.4:8080/v1/chat/completions"
    assert payload["model"] == "qwen3.6-35b-a3b:code"
    assert payload["max_tokens"] == 256


@pytest.mark.asyncio
async def test_batch_classification_falls_back_to_individual_on_bad_json(monkeypatch):
    monkeypatch.setattr(
        classifier_mod,
        "get_settings",
        lambda: SimpleNamespace(
            resolved_classification_model="model",
            openai_base_url="http://localhost:8080",
            openai_classification_url=None,
            classification_timeout_seconds=90.0,
            classification_max_concurrent=1,
            classification_batch_size=10,
            classification_temperature=0.0,
            classification_openai_max_tokens=64,
            classification_openai_batch_min_tokens=256,
            classification_openai_batch_tokens_per_job=48,
            classification_parse_retry_attempts=0,
        ),
    )
    classifier = classifier_mod.JobClassifier()
    batch_calls = 0
    individual_calls = 0

    async def _bad_batch(_jobs):
        nonlocal batch_calls
        batch_calls += 1
        return [(None, "invalid_json", "not json"), (None, "invalid_json", "not json")]

    async def _individual(jobs):
        nonlocal individual_calls
        individual_calls += len(jobs)
        return [("software_engineering", "ok", ""), ("finance", "ok", "")]

    monkeypatch.setattr(classifier._client, "classify_prompt_batch_with_reasons", _bad_batch)
    monkeypatch.setattr(classifier, "classify_batch_individually_with_reasons", _individual)

    result = await classifier.classify_batch_with_reasons(
        [("Software Engineer", "Build APIs"), ("Finance Analyst", "Analyze budgets")]
    )

    assert result == [("software_engineering", "ok"), ("finance", "ok")]
    assert batch_calls == 1
    assert individual_calls == 2
