"""Embedding service for generating text embeddings using Ollama or LM Studio."""

from __future__ import annotations

import re
from typing import Iterable

import httpx

from app.config import get_settings


class EmbeddingService:
    """Async embedding service supporting Ollama and LM Studio (OpenAI-compatible)."""

    def __init__(self, model: str | None = None) -> None:
        self._settings = get_settings()
        self._provider = self._settings.embedding_provider
        self._model = model or self._settings.embedding_model or "nomic-embed-text"
        # Strip trailing slash to avoid double slashes
        self._base_url = self._settings.ollama_base_url.rstrip("/")

    def _clean_text(
        self, text: str, max_chars_ascii: int = 6000, max_chars_unicode: int = 2000
    ) -> str:
        """Clean and truncate text for embedding.

        Uses higher limit for ASCII text (English) and lower limit for
        non-ASCII text (Japanese, Chinese, etc.) which uses more tokens per char.
        """
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        # Check if text is mostly ASCII (a-z, 0-9, common punctuation)
        ascii_chars = sum(1 for c in text if ord(c) < 128)
        is_mostly_ascii = len(text) == 0 or (ascii_chars / len(text)) > 0.8

        # Use appropriate limit based on character type
        max_chars = max_chars_ascii if is_mostly_ascii else max_chars_unicode

        # Truncate to max chars
        if len(text) > max_chars:
            text = text[:max_chars]
        return text

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        # Clean and truncate text to prevent context length errors
        text = self._clean_text(text)

        if self._provider == "lmstudio":
            return await self._embed_lmstudio(text)
        else:
            return await self._embed_ollama(text)

    async def embed_many(self, texts: Iterable[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        texts_list = list(texts)
        # Both providers don't support true batch, so we do one at a time
        return [await self.embed(text) for text in texts_list]

    async def _embed_ollama(self, text: str) -> list[float]:
        """Generate embedding using native Ollama API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._base_url}/api/embeddings",
                    json={
                        "model": self._model,
                        "prompt": text,
                        "options": {"num_ctx": 16384},  # Increase context window
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
        try:
            async with httpx.AsyncClient() as client:
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
        # OpenAI format: data.data[0].embedding
        if "data" not in data or not data["data"] or "embedding" not in data["data"][0]:
            raise RuntimeError(
                "LM Studio response missing embedding data. "
                f"Base URL: {self._base_url}. Response keys: {list(data.keys())}"
            )

        return data["data"][0]["embedding"]
