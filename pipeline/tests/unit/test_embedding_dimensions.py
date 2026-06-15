"""Unit tests for core embedding service (pipeline consumer)."""

from __future__ import annotations

import pytest

from internnexus_core.embedding import (
    OPENAI_COMPATIBLE_PROVIDER,
    EmbeddingConfig,
    QueryEmbeddingService,
)


@pytest.mark.asyncio
async def test_openai_compatible_embedding_request_includes_configured_dimensions(monkeypatch):
    calls: list[tuple[str, dict[str, object], float]] = []

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, list[dict[str, list[float]]]]:
            return {"data": [{"embedding": [0.1, 0.2, 0.3]}]}

    class _Client:
        async def post(self, url: str, json: dict[str, object], timeout: float):
            calls.append((url, json, timeout))
            return _Response()

    from internnexus_core import embedding as core_embedding

    monkeypatch.setattr(core_embedding, "get_http_client", lambda: _Client())

    cfg = EmbeddingConfig(
        provider=OPENAI_COMPATIBLE_PROVIDER,
        model="qwen3-embedding-4b",
        dimensions=2,
        base_url="http://192.168.0.4:8080",
    )
    service = QueryEmbeddingService(config=cfg)
    result = await service._embed_openai_compatible_impl("software engineer intern")

    assert result == [0.1, 0.2]
    assert calls == [
        (
            "http://192.168.0.4:8080/v1/embeddings",
            {
                "model": "qwen3-embedding-4b",
                "input": "software engineer intern",
                "dimensions": 2,
            },
            60.0,
        )
    ]


@pytest.mark.asyncio
async def test_openai_compatible_embed_many_uses_one_index_ordered_request(monkeypatch):
    calls: list[tuple[str, dict[str, object], float]] = []

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, list[dict[str, object]]]:
            return {
                "data": [
                    {"index": 1, "embedding": [2.0, 2.1, 2.2]},
                    {"index": 0, "embedding": [1.0, 1.1, 1.2]},
                    {"index": 2, "embedding": [3.0, 3.1, 3.2]},
                ]
            }

    class _Client:
        async def post(self, url: str, json: dict[str, object], timeout: float):
            calls.append((url, json, timeout))
            return _Response()

    from internnexus_core import embedding as core_embedding

    monkeypatch.setattr(core_embedding, "get_http_client", lambda: _Client())

    cfg = EmbeddingConfig(
        provider=OPENAI_COMPATIBLE_PROVIDER,
        model="qwen3-embedding-4b",
        dimensions=2,
        base_url="http://192.168.0.4:8080",
    )
    service = QueryEmbeddingService(config=cfg)
    result = await service.embed_many(["first", "second", "third"], batch_size=3)

    assert result == [[1.0, 1.1], [2.0, 2.1], [3.0, 3.1]]
    assert calls == [
        (
            "http://192.168.0.4:8080/v1/embeddings",
            {
                "model": "qwen3-embedding-4b",
                "input": ["first", "second", "third"],
                "dimensions": 2,
            },
            60.0,
        )
    ]
