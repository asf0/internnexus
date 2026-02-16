"""Embedding service for generating text embeddings using Ollama or LM Studio."""

from __future__ import annotations

import asyncio
import re
from typing import Iterable

import httpx

from app.config import get_settings
from app.http_client.client import get_http_client


class EmbeddingService:
    """Async embedding service supporting Ollama and LM Studio (OpenAI-compatible)."""

    def __init__(self, model: str | None = None) -> None:
        self._settings = get_settings()
        self._provider = self._settings.embedding_provider
        self._model = model or self._settings.embedding_model or "nomic-embed-text"
        self._base_url = self._settings.ollama_base_url.rstrip("/")

    def _clean_text(
        self, text: str, max_chars_ascii: int = 6000, max_chars_unicode: int = 2000
    ) -> str:
        """Clean and truncate text for embedding.

        Uses higher limit for ASCII text (English) and lower limit for
        non-ASCII text (Japanese, Chinese, etc.) which uses more tokens per char.
        """
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        ascii_chars = sum(1 for c in text if ord(c) < 128)
        is_mostly_ascii = len(text) == 0 or (ascii_chars / len(text)) > 0.8

        max_chars = max_chars_ascii if is_mostly_ascii else max_chars_unicode

        if len(text) > max_chars:
            text = text[:max_chars]
        return text

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        text = self._clean_text(text)

        if self._provider == "lmstudio":
            return await self._embed_lmstudio(text)
        else:
            return await self._embed_ollama(text)

    async def embed_many(self, texts: Iterable[str], batch_size: int = 10) -> list[list[float]]:
        """Generate embeddings for multiple texts with concurrent batching."""
        texts_list = list(texts)
        results = []

        for i in range(0, len(texts_list), batch_size):
            batch = texts_list[i : i + batch_size]
            batch_results = await asyncio.gather(*[self.embed(t) for t in batch])
            results.extend(batch_results)

        return results

    async def _embed_ollama(self, text: str) -> list[float]:
        """Generate embedding using native Ollama API."""
        client = get_http_client()
        try:
            response = await client.post(
                f"{self._base_url}/api/embeddings",
                json={
                    "model": self._model,
                    "prompt": text,
                    "options": {"num_ctx": 16384},
                },
                timeout=60.0,
            )
            response.raise_for_status()
        except httpx.RequestError as exc:
            raise RuntimeError(
                f"Ollama connection failed. Base URL: {self._base_url}. Error: {exc}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500] if exc.response is not None else ""
            raise RuntimeError(
                "Ollama request failed. "
                f"Status: {exc.response.status_code if exc.response else 'unknown'}. "
                f"Base URL: {self._base_url}. Response: {detail}"
            ) from exc

        data = response.json()
        if "embedding" not in data:
            raise RuntimeError(
                "Ollama response missing 'embedding'. "
                f"Base URL: {self._base_url}. Response keys: {list(data.keys())}"
            )

        return data["embedding"]

    async def _embed_lmstudio(self, text: str) -> list[float]:
        """Generate embedding using LM Studio OpenAI-compatible API."""
        client = get_http_client()
        try:
            response = await client.post(
                f"{self._base_url}/v1/embeddings",
                json={
                    "model": self._model,
                    "input": text,
                },
                timeout=60.0,
            )
            response.raise_for_status()
        except httpx.RequestError as exc:
            raise RuntimeError(
                f"LM Studio connection failed. Base URL: {self._base_url}. Error: {exc}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500] if exc.response is not None else ""
            raise RuntimeError(
                "LM Studio request failed. "
                f"Status: {exc.response.status_code if exc.response else 'unknown'}. "
                f"Base URL: {self._base_url}. Response: {detail}"
            ) from exc

        data = response.json()
        if "data" not in data or not data["data"] or "embedding" not in data["data"][0]:
            raise RuntimeError(
                "LM Studio response missing embedding data. "
                f"Base URL: {self._base_url}. Response keys: {list(data.keys())}"
            )

        return data["data"][0]["embedding"]
