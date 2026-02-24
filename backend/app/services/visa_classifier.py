from __future__ import annotations
import json
from pathlib import Path
from typing import Any

import httpx

from app.config import get_settings

VisaResult = dict[str, Any]


def _load_system_prompt() -> str:
    """Load system prompt from file."""
    prompt_path = Path(__file__).resolve().parents[2] / "prompts" / "visa_classifier.txt"
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        # Fallback to basic prompt if file not found
        return (
            "Analyze text for US Visa Sponsorship and F1/OPT/CPT friendliness. "
            "Return JSON: { 'visa': bool, 'f1': bool, 'reasoning': str }."
        )


class VisaClassifier:
    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.ollama_base_url
        self._model = settings.classification_model
        self._provider = settings.embedding_provider
        self._system_prompt = _load_system_prompt()

    def classify(self, description_text: str) -> tuple[VisaResult, dict]:
        """Classify job and return result with token usage.

        Returns:
            Tuple of (classification_result, token_usage)
            token_usage: {"total_tokens": int, "prompt_tokens": int, "completion_tokens": int}
        """
        if not self._model:
            raise RuntimeError("CLASSIFICATION_MODEL not set in .env")

        if self._provider == "lmstudio":
            return self._classify_lmstudio(description_text)
        else:
            return self._classify_ollama(description_text)

    def _classify_ollama(self, description_text: str) -> tuple[VisaResult, dict]:
        """Classify using Ollama and return result with token usage."""
        if not self._model:
            raise RuntimeError("CLASSIFICATION_MODEL not set in .env")

        try:
            response = httpx.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": self._system_prompt},
                        {"role": "user", "content": description_text},
                    ],
                    "format": "json",
                    "stream": False,
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
                f"Ollama request failed. Status: {exc.response.status_code if exc.response else 'unknown'}. "
                f"Base URL: {self._base_url}. Response: {detail}"
            ) from exc

        data = response.json()
        content = data.get("message", {}).get("content", "{}")
        result = self._parse_json(content)

        # Extract token usage from Ollama response
        tokens = self._extract_token_usage(data)

        return result, tokens

    def _extract_token_usage(self, data: dict) -> dict:
        """Extract token usage from API response.

        Returns dict with total_tokens, prompt_tokens, completion_tokens.
        Returns zeros if usage data not available.
        """
        usage = data.get("usage", {})

        # Try to get from OpenAI-compatible format first
        if usage:
            return {
                "total_tokens": usage.get("total_tokens", 0),
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            }

        # Fallback to Ollama format (if available)
        eval_count = data.get("eval_count", 0)  # Completion tokens
        prompt_eval_count = data.get("prompt_eval_count", 0)  # Prompt tokens

        if eval_count or prompt_eval_count:
            return {
                "total_tokens": eval_count + prompt_eval_count,
                "prompt_tokens": prompt_eval_count,
                "completion_tokens": eval_count,
            }

        # No usage data available
        return {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
        }

    def _classify_lmstudio(self, description_text: str) -> tuple[VisaResult, dict]:
        """Classify using LM Studio and return result with token usage."""
        try:
            response = httpx.post(
                f"{self._base_url}/v1/chat/completions",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": self._system_prompt},
                        {"role": "user", "content": description_text},
                    ],
                    "stream": False,
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
                f"LM Studio request failed. Status: {exc.response.status_code if exc.response else 'unknown'}. "
                f"Base URL: {self._base_url}. Response: {detail}"
            ) from exc

        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        result = self._parse_json(content)

        # Extract token usage
        tokens = self._extract_token_usage(data)

        return result, tokens

    @staticmethod
    def _parse_json(raw: str) -> VisaResult:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {}
        return {
            "visa": bool(payload.get("visa", False)),
            "f1": bool(payload.get("f1", False)),
            "reasoning": str(payload.get("reasoning", "")),
        }
