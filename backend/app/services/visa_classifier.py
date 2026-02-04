from __future__ import annotations

import json
from typing import Any, Literal

from anthropic import Anthropic
from openai import OpenAI

from app.config import get_settings

VisaResult = dict[str, Any]


SYSTEM_PROMPT = (
    "Analyze text for US Visa Sponsorship and F1/OPT/CPT friendliness. "
    "Return JSON: { 'visa': bool, 'f1': bool, 'reasoning': str }."
)


class VisaClassifier:
    def __init__(self) -> None:
        settings = get_settings()
        self._openai_key = settings.openai_api_key
        self._anthropic_key = settings.anthropic_api_key

        if not self._openai_key and not self._anthropic_key:
            raise RuntimeError("OPENAI_API_KEY or ANTHROPIC_API_KEY is required for visa classification.")

        self._openai_client = OpenAI(api_key=self._openai_key) if self._openai_key else None
        self._anthropic_client = (
            Anthropic(api_key=self._anthropic_key) if self._anthropic_key else None
        )

    def classify(self, description_text: str) -> VisaResult:
        if self._openai_client:
            return self._classify_openai(description_text)
        return self._classify_anthropic(description_text)

    def _classify_openai(self, description_text: str) -> VisaResult:
        response = self._openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": description_text},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        return self._parse_json(content)

    def _classify_anthropic(self, description_text: str) -> VisaResult:
        response = self._anthropic_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": description_text}],
        )
        content = "".join(block.text for block in response.content)
        return self._parse_json(content)

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
