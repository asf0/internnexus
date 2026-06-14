"""Unit tests for core embedding service."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from internnexus_core.embedding import (
    EmbeddingConfig,
    EmbeddingError,
    QueryEmbeddingService,
    RateLimitError,
    _is_retryable_exception,
)


class TestEmbeddingConfig:
    def test_defaults(self):
        cfg = EmbeddingConfig()
        assert cfg.provider == "ollama"
        assert cfg.model == "nomic-embed-text"
        assert cfg.dimensions == 2560
        assert cfg.base_url == "http://localhost:11434"

    def test_custom_values(self):
        cfg = EmbeddingConfig(
            provider="lmstudio",
            model="custom-model",
            dimensions=1024,
            base_url="http://custom:8080",
        )
        assert cfg.provider == "lmstudio"
        assert cfg.model == "custom-model"
        assert cfg.dimensions == 1024
        assert cfg.base_url == "http://custom:8080"


class TestRetryableException:
    def test_embedding_error_retryable(self):
        assert _is_retryable_exception(EmbeddingError("fail", retryable=True)) is True

    def test_embedding_error_non_retryable(self):
        assert _is_retryable_exception(EmbeddingError("fail", retryable=False)) is False

    def test_cancelled_error_not_retryable(self):
        assert _is_retryable_exception(asyncio.CancelledError()) is False


import asyncio


class TestQueryEmbeddingService:
    def test_init_uses_default_config(self):
        service = QueryEmbeddingService()
        assert service._provider == "ollama"
        assert service._model == "nomic-embed-text"
        assert service._dimensions == 2560
        assert service._base_url == "http://localhost:11434"

    def test_init_uses_custom_config(self):
        cfg = EmbeddingConfig(
            provider="lmstudio",
            model="test-model",
            dimensions=512,
            base_url="http://test:8080",
        )
        service = QueryEmbeddingService(config=cfg)
        assert service._provider == "lmstudio"
        assert service._model == "test-model"
        assert service._dimensions == 512
        assert service._base_url == "http://test:8080"

    def test_init_model_override(self):
        cfg = EmbeddingConfig(model="default-model")
        service = QueryEmbeddingService(config=cfg, model="override-model")
        assert service._model == "override-model"

    def test_base_url_trailing_stripped(self):
        cfg = EmbeddingConfig(base_url="http://test:8080/")
        service = QueryEmbeddingService(config=cfg)
        assert service._base_url == "http://test:8080"


@pytest.mark.asyncio
async def test_lmstudio_embedding_request_includes_dimensions(monkeypatch):
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
        provider="lmstudio",
        model="qwen3-embedding-4b",
        dimensions=2,
        base_url="http://192.168.0.4:8080",
    )
    service = QueryEmbeddingService(config=cfg)
    result = await service._embed_lmstudio_impl("software engineer intern")

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
async def test_lmstudio_embed_many_uses_one_index_ordered_request(monkeypatch):
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
        provider="lmstudio",
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


class TestEmbeddingError:
    def test_base_error_retryable_default(self):
        err = EmbeddingError("test")
        assert err.retryable is False

    def test_base_error_retryable_true(self):
        err = EmbeddingError("test", retryable=True)
        assert err.retryable is True

    def test_rate_limit_error(self):
        err = RateLimitError("rate limited", retry_after=5.0)
        assert err.retryable is True
        assert err.retry_after == 5.0
