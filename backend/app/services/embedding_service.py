from __future__ import annotations

import re
from typing import Iterable

import httpx
from openai import OpenAI

from app.config import get_settings


class EmbeddingService:
    def __init__(self, model: str | None = None) -> None:
        self._settings = get_settings()
        self._provider = self._settings.embedding_provider
        
        if self._provider == "ollama":
            self._model = model or self._settings.embedding_model or "nomic-embed-text"
            self._base_url = self._settings.ollama_base_url
        elif self._provider == "openai":
            if not self._settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is required for OpenAI embeddings.")
            self._client = OpenAI(api_key=self._settings.openai_api_key)
            self._model = model or self._settings.embedding_model or "text-embedding-3-small"
        else:
            raise RuntimeError(f"Unknown embedding provider: {self._provider}")

    def _clean_text(self, text: str, max_chars_ascii: int = 6000, max_chars_unicode: int = 2000) -> str:
        """Clean and truncate text for embedding.
        
        Uses higher limit for ASCII text (English) and lower limit for 
        non-ASCII text (Japanese, Chinese, etc.) which uses more tokens per char.
        """
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
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

    def embed(self, text: str) -> list[float]:
        # Clean and truncate text to prevent context length errors
        text = self._clean_text(text)
        
        if self._provider == "ollama":
            return self._embed_ollama(text)
        else:
            response = self._client.embeddings.create(model=self._model, input=text)
            return list(response.data[0].embedding)

    def embed_many(self, texts: Iterable[str]) -> list[list[float]]:
        texts_list = list(texts)
        if self._provider == "ollama":
            # Ollama doesn't support batch, so we do one at a time
            return [self._embed_ollama(text) for text in texts_list]
        else:
            response = self._client.embeddings.create(model=self._model, input=texts_list)
            return [list(item.embedding) for item in response.data]

    def _embed_ollama(self, text: str) -> list[float]:
        try:
            response = httpx.post(
                f"{self._base_url}/api/embeddings",
                json={
                    "model": self._model,
                    "prompt": text,
                    "options": {"num_ctx": 16384}  # Increase context window
                },
                timeout=60.0,
            )
            response.raise_for_status()
        except httpx.RequestError as exc:
            raise RuntimeError(
                "Ollama connection failed. "
                f"Base URL: {self._base_url}. Error: {exc}"
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
