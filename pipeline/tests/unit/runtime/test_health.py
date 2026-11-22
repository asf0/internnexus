"""Health check regressions for OpenAI-compatible embedding responses."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from pipeline.runtime import health


class _Response:
    def __init__(self, embedding: Any) -> None:
        self._embedding = embedding

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {"data": [{"embedding": self._embedding}]}


class _Client:
    def __init__(self, embedding: Any) -> None:
        self._embedding = embedding

    async def __aenter__(self) -> _Client:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def post(self, _url: str, **_kwargs: object) -> _Response:
        return _Response(self._embedding)


def _settings(dimensions: int) -> SimpleNamespace:
    return SimpleNamespace(
        openai_base_url="http://embed/v1",
        embedding_model="model",
        embedding_dimensions=dimensions,
    )


async def test_check_embedding_service_truncates_oversize_matryoshka_vectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health, "get_settings", lambda: _settings(4))
    monkeypatch.setattr(health.httpx, "AsyncClient", lambda **_kwargs: _Client([0.1] * 8))

    result = await health.check_embedding_service()

    assert result.healthy is True
    assert result.details == {"url": "http://embed/v1/embeddings", "dimensions": 4}


async def test_check_embedding_service_rejects_undersize_vectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health, "get_settings", lambda: _settings(4))
    monkeypatch.setattr(health.httpx, "AsyncClient", lambda **_kwargs: _Client([0.1] * 2))

    result = await health.check_embedding_service()

    assert result.healthy is False
    assert "expected at least 4 dimensions, received 2" in result.message
