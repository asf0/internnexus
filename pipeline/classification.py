"""LLM-based job classification service using Ollama or LM Studio."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from pipeline.backend_bridge import get_settings
from pipeline.category_mapping import (
    CANONICAL_CATEGORIES,
    CATEGORY_MAPPING,
    INVALID_CATEGORIES,
)

logger = logging.getLogger(__name__)

# Default timeout for classification requests (seconds)
DEFAULT_TIMEOUT = 90.0

# Maximum concurrent requests for batch processing
MAX_CONCURRENT_REQUESTS = 2

# Maximum description length to send to LLM (chars)
MAX_DESCRIPTION_LENGTH = 500

# Valid category pattern (lowercase letters, numbers, underscores)
VALID_CATEGORY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

# Use all canonical categories - LLM must choose from this exact list
VALID_CATEGORIES = CANONICAL_CATEGORIES
CANDIDATE_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_\-]+")
MAX_REJECTION_SAMPLES_PER_BATCH = 5
LOW_SIGNAL_REJECTION_TOKENS = {
    "a",
    "an",
    "and",
    "category",
    "job",
    "m",
    "n_a",
    "na",
    "none",
    "null",
    "or",
    "other",
    "test",
    "the",
    "unknown",
}

CATEGORY_HINTS: dict[str, str] = {
    "software_engineering": "backend frontend full_stack api platform",
    "data_science": "analytics experimentation modeling insights statistics",
    "data_engineering": "etl pipelines warehousing spark airflow",
    "machine_learning": "ml ai model_training inference llm",
    "product_management": "roadmap prioritization requirements stakeholders",
    "product_design": "ux ui interaction visual design",
    "sales": "account_executive bdr quota pipeline gtm",
    "marketing": "brand growth campaign paid_media seo",
    "operations": "process execution coordination service delivery",
    "finance": "fp_and_a budgeting revenue accounting_strategy",
    "hr": "people_ops talent_acquisition employee_relations",
    "customer_success": "onboarding retention adoption account_health",
    "security": "application_security infosec cyber risk controls",
    "devops": "infra deployment ci_cd sre reliability",
    "legal": "counsel contracts compliance legal_ops",
    "healthcare": "clinical patient_care nursing medical",
    "research": "r_and_d scientific_research lab",
    "consulting": "advisory professional_services implementation",
    "project_management": "program_management delivery planning pmo",
    "quality_assurance": "qa testing validation test_automation",
    "hardware_engineering": "electrical mechanical firmware manufacturing",
    "content_writing": "writing editorial content technical_writing",
    "translation": "localization linguist translation",
    "education": "training instructional learning enablement",
    "construction": "field_construction trades site_ops",
    "accounting": "bookkeeping close gl ar ap",
    "compliance": "regulatory aml kyc controls monitoring",
    "risk_management": "risk assessment governance mitigation",
    "recruiting": "recruiter sourcing interviewing hiring",
    "customer_support": "helpdesk support tickets troubleshooting",
    "logistics_supply_chain": "fulfillment warehouse logistics procurement",
}


def _is_high_signal_unmapped_candidate(category: str) -> bool:
    """Return True when a rejected candidate is useful for curation."""
    if not category:
        return False
    if category in LOW_SIGNAL_REJECTION_TOKENS:
        return False
    if category in INVALID_CATEGORIES:
        return False
    if category.isdigit() or len(category) < 3:
        return False
    return True


def _extract_rejection_slug_candidates(raw_output: str) -> set[str]:
    """Extract likely slug candidates from rejected model output."""
    candidates: set[str] = set()
    for raw_token in CANDIDATE_TOKEN_PATTERN.findall(raw_output):
        normalized = _normalize_slug_token(raw_token)
        if not normalized:
            continue
        if "_" not in normalized and len(normalized) < 4:
            continue
        if not _is_high_signal_unmapped_candidate(normalized):
            continue
        candidates.add(normalized)
    return candidates


def _write_unmapped_categories(candidates: set[str]) -> int:
    """Merge rejected slug candidates into unmapped_categories.json.

    Returns the number of newly-added slugs.
    """
    if not candidates:
        return 0

    log_path = Path(os.getenv("DATA_DIR", "data")) / "unmapped_categories.json"
    existing: set[str] = set()
    if log_path.exists():
        try:
            existing = set(json.loads(log_path.read_text()))
        except json.JSONDecodeError:
            existing = set()

    before = len(existing)
    existing.update(candidates)
    added = len(existing) - before
    if added:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps(sorted(existing), indent=2) + "\n")
    return added


def _append_rejection_events(events: list[dict[str, str]]) -> None:
    """Append non-tokenizable classification rejections for review."""
    if not events:
        return

    log_path = Path(os.getenv("DATA_DIR", "data")) / "classification_rejections.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        for event in events:
            fh.write(json.dumps(event, ensure_ascii=True) + "\n")


class ClassificationError(Exception):
    """Base exception for classification failures."""

    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class RateLimitError(ClassificationError):
    """Rate limit exceeded - retryable."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message, retryable=True)
        self.retry_after = retry_after


def _is_retryable_exception(exc: BaseException) -> bool:
    """Determine if an exception is retryable."""
    if isinstance(exc, asyncio.CancelledError):
        return False
    if isinstance(exc, ClassificationError):
        return exc.retryable
    if isinstance(exc, (httpx.RequestError, httpx.TimeoutException)):
        return True
    return False


_retry_decorator = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception(lambda e: _is_retryable_exception(e)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


def _build_category_cards() -> str:
    """Render compact category cards with keyword hints."""
    cards = []
    for slug in VALID_CATEGORIES:
        hints = CATEGORY_HINTS.get(slug, slug.replace("_", " "))
        cards.append(f"- {slug}: {hints}")
    return "\n".join(cards)


def _build_classification_prompts(title: str, description: str) -> tuple[str, str]:
    """Build deterministic system/user prompts for classification."""
    truncated_desc = description[:MAX_DESCRIPTION_LENGTH]
    if len(description) > MAX_DESCRIPTION_LENGTH:
        truncated_desc += "..."

    system_prompt = """You classify job postings into exactly one allowed category slug.
Rules:
- Return JSON only: {\"category\":\"<allowed_slug>\"}
- category must be one slug from the allowed list
- Never invent or transform a new slug
- If uncertain, choose the nearest allowed slug"""

    user_prompt = f"""Allowed categories:
{_build_category_cards()}

Title: {title}
Description: {truncated_desc}

Return JSON only, example: {{"category":"software_engineering"}}"""

    return system_prompt, user_prompt


def _extract_json_category(raw_output: str) -> str | None:
    """Extract category value from JSON output if present."""
    if not raw_output:
        return None

    text = raw_output.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    category_value = payload.get("category")
    if not isinstance(category_value, str):
        return None
    return _normalize_slug_token(category_value)


def _normalize_slug_token(raw_token: str) -> str | None:
    """Normalize one token candidate into a category-like slug."""
    if not raw_token:
        return None

    category = raw_token.strip().strip("\"'").lower()
    category = re.sub(r"[\s\-]+", "_", category)
    category = re.sub(r"[^a-z0-9_]", "", category)
    category = category.strip("_")
    category = re.sub(r"_+", "_", category)

    if not category or not VALID_CATEGORY_PATTERN.match(category):
        return None
    return category


def _extract_canonical_category(raw_output: str) -> tuple[str | None, str]:
    """Extract the first valid canonical category from model output."""
    if not raw_output or not raw_output.strip():
        return None, "empty_response"

    json_category = _extract_json_category(raw_output)
    if json_category:
        canonical = _map_category_strict(json_category)
        if canonical:
            return canonical, "ok"

    for raw_token in CANDIDATE_TOKEN_PATTERN.findall(raw_output):
        normalized = _normalize_slug_token(raw_token)
        if not normalized:
            continue
        canonical = _map_category_strict(normalized)
        if canonical:
            return canonical, "ok"

    return None, "no_mappable_token"


def _map_category_strict(category: str) -> str | None:
    """Strict category mapping that does not fall back to operations."""
    category_lower = category.lower().strip()
    if not category_lower:
        return None

    normalized = category_lower
    for region_suffix in ("_apac", "_emea", "_latam", "_na", "_us", "_uk"):
        if normalized.endswith(region_suffix):
            normalized = normalized[: -len(region_suffix)]
            break

    if normalized in INVALID_CATEGORIES:
        return None
    if normalized in CANONICAL_CATEGORIES:
        return normalized
    if normalized in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[normalized]

    for prefix, canonical in (
        ("legal_", "legal"),
        ("hr_", "hr"),
        ("employee_", "hr"),
        ("patient_", "healthcare"),
        ("clinical_", "healthcare"),
    ):
        if normalized.startswith(prefix):
            return canonical

    if normalized.startswith("field_") and "sales" in normalized:
        return "sales"
    if normalized.startswith("field_") and "care" in normalized:
        return "healthcare"
    if normalized.endswith("_sales"):
        return "sales"
    if normalized.endswith("_consulting") or normalized.endswith("_consultant"):
        return "consulting"
    if normalized.endswith("_training"):
        return "education"

    for suffix in ["_engineering", "_management", "_operations", "_development", "_analysis"]:
        if normalized.endswith(suffix):
            base = normalized[: -len(suffix)]
            if base in CATEGORY_MAPPING:
                return CATEGORY_MAPPING[base]
            if base in CANONICAL_CATEGORIES:
                return base
    return None


class JobClassifier:
    """Async job classification service supporting Ollama and LM Studio."""

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        provider: str | None = None,
        timeout: float | None = None,
        max_concurrent: int | None = None,
    ) -> None:
        """Initialize the classifier.

        Args:
            model: Model name (defaults to settings.classification_model)
            base_url: API URL (defaults to settings.ollama_base_url)
            provider: "ollama" or "lmstudio" (defaults to settings.embedding_provider)
            timeout: Request timeout in seconds
            max_concurrent: Maximum concurrent requests for batch processing
        """
        settings = get_settings()
        self._model = model or settings.resolved_classification_model
        self._base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._provider = provider or settings.embedding_provider
        configured_timeout = float(getattr(settings, "classification_timeout_seconds", DEFAULT_TIMEOUT))
        configured_concurrency = int(getattr(settings, "classification_max_concurrent", MAX_CONCURRENT_REQUESTS))
        self._timeout = float(timeout) if timeout is not None else configured_timeout
        self._max_concurrent = int(max_concurrent) if max_concurrent is not None else configured_concurrency
        self._keep_alive = str(getattr(settings, "classification_keep_alive", "30m"))
        self._num_predict = int(getattr(settings, "classification_num_predict", 20))
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(self._timeout, connect=10.0))
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def classify_job(self, title: str, description: str) -> str | None:
        """Classify a single job into a category.

        Args:
            title: Job title
            description: Job description text

        Returns:
            Category slug (e.g., "software_engineering") or None if classification fails
        """
        category, _reason, _raw_output = await self._classify_job_with_reason(title, description)
        return category

    async def _classify_job_with_reason(self, title: str, description: str) -> tuple[str | None, str, str]:
        """Classify a single job and return category, reason, and raw output sample."""
        try:
            if self._provider == "lmstudio":
                return await self._classify_lmstudio(title, description)
            return await self._classify_ollama(title, description)
        except asyncio.CancelledError:
            logger.warning("Classification request cancelled")
            raise
        except ClassificationError as e:
            logger.warning(f"Classification failed for '{title}': {e}")
            return None, "http_or_timeout_error", ""
        except Exception as e:
            logger.error(f"Unexpected classification error for '{title}': {e}")
            return None, "unexpected_error", ""

    async def _classify_ollama(self, title: str, description: str) -> tuple[str | None, str, str]:
        """Classify using Ollama native API."""
        return await self._classify_ollama_impl(title, description)

    @_retry_decorator
    async def _classify_ollama_impl(self, title: str, description: str) -> tuple[str | None, str, str]:
        """Classify using Ollama native API (with retry)."""
        system_prompt, user_prompt = _build_classification_prompts(title, description)
        prompt = f"SYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}"
        client = await self._get_client()

        try:
            response = await client.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": self._keep_alive,
                    "options": {
                        "temperature": 0.0,
                        "num_predict": self._num_predict,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
        except asyncio.CancelledError:
            raise
        except httpx.TimeoutException as exc:
            raise ClassificationError(
                f"Ollama classification timed out for '{title}': {exc}",
                retryable=True,
            ) from exc
        except httpx.RequestError as exc:
            raise ClassificationError(
                f"Ollama connection failed for '{title}': {exc}",
                retryable=True,
            ) from exc
        except httpx.HTTPStatusError as exc:
            self._handle_http_error(exc, title, "Ollama")
            raise AssertionError("unreachable")

        raw_output = data.get("response", "")
        category, reason = _extract_canonical_category(raw_output)
        return category, reason, raw_output

    async def _classify_lmstudio(self, title: str, description: str) -> tuple[str | None, str, str]:
        """Classify using LM Studio OpenAI-compatible API."""
        return await self._classify_lmstudio_impl(title, description)

    @_retry_decorator
    async def _classify_lmstudio_impl(self, title: str, description: str) -> tuple[str | None, str, str]:
        """Classify using LM Studio OpenAI-compatible API (with retry)."""
        system_prompt, user_prompt = _build_classification_prompts(title, description)
        client = await self._get_client()

        try:
            # LM Studio uses OpenAI-compatible chat completions API
            response = await client.post(
                f"{self._base_url}/v1/chat/completions",
                json={
                    "model": self._model,
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {
                            "role": "user",
                            "content": user_prompt,
                        },
                    ],
                    "temperature": 0.0,
                    "max_tokens": 32,
                },
            )
            response.raise_for_status()
            data = response.json()
        except asyncio.CancelledError:
            raise
        except httpx.TimeoutException as exc:
            raise ClassificationError(
                f"LM Studio classification timed out for '{title}': {exc}",
                retryable=True,
            ) from exc
        except httpx.RequestError as exc:
            raise ClassificationError(
                f"LM Studio connection failed for '{title}': {exc}",
                retryable=True,
            ) from exc
        except httpx.HTTPStatusError as exc:
            self._handle_http_error(exc, title, "LM Studio")
            raise AssertionError("unreachable")

        # Parse OpenAI-compatible response
        choices = data.get("choices", [])
        if not choices:
            logger.warning(f"No choices in LM Studio response for '{title}'")
            return None, "empty_response", ""

        message = choices[0].get("message", {})
        raw_output = message.get("content", "")
        category, reason = _extract_canonical_category(raw_output)
        return category, reason, raw_output

    def _handle_http_error(self, exc: httpx.HTTPStatusError, title: str, provider: str) -> None:
        """Handle HTTP status errors."""
        status_code = exc.response.status_code if exc.response else 0
        detail = exc.response.text[:500] if exc.response is not None else ""

        if status_code == 429:
            retry_after = None
            if exc.response and "retry-after" in exc.response.headers:
                try:
                    retry_after = float(exc.response.headers["retry-after"])
                except (ValueError, TypeError):
                    pass
            raise RateLimitError(
                f"{provider} rate limited. Retry-After: {retry_after}",
                retry_after=retry_after,
            ) from exc
        elif status_code >= 500:
            raise ClassificationError(
                f"{provider} server error ({status_code}) for '{title}': {detail}",
                retryable=True,
            ) from exc
        else:
            raise ClassificationError(
                f"{provider} request failed ({status_code}) for '{title}': {detail}",
                retryable=False,
            ) from exc

    async def classify_batch_with_reasons(self, jobs: list[tuple[str, str]]) -> list[tuple[str | None, str]]:
        """Classify multiple jobs concurrently with rate limiting.

        Args:
            jobs: List of (title, description) tuples

        Returns:
            List of (category slug or None, reason) in input order
        """
        if not jobs:
            return []

        semaphore = asyncio.Semaphore(self._max_concurrent)
        completed = 0
        lock = asyncio.Lock()

        async def classify_with_semaphore(idx: int, title: str, description: str) -> tuple[int, str | None, str, str]:
            nonlocal completed
            async with semaphore:
                try:
                    result, reason, raw_output = await self._classify_job_with_reason(title, description)
                except Exception as e:
                    logger.error(f"Error classifying job '{title}': {e}")
                    result = None
                    reason = "unexpected_error"
                    raw_output = ""

                async with lock:
                    completed += 1
                    if completed % 10 == 0:
                        logger.info(f"Classification progress: {completed}/{len(jobs)}")

                return (idx, result, reason, raw_output)

        tasks = [classify_with_semaphore(i, title, description) for i, (title, description) in enumerate(jobs)]

        try:
            results_with_idx = await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.warning("Batch classification cancelled")
            raise

        results: list[tuple[str | None, str]] = [(None, "empty_response")] * len(jobs)
        rejection_reasons: dict[str, int] = {}
        rejection_samples: dict[str, list[str]] = {}
        rejected_slug_candidates: set[str] = set()
        rejection_events: list[dict[str, str]] = []
        for idx, result, reason, raw_output in results_with_idx:
            results[idx] = (result, reason)
            if result is None:
                rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
                title, _description = jobs[idx]
                if raw_output:
                    compact = " ".join(raw_output.strip().split())
                    samples = rejection_samples.setdefault(reason, [])
                    if len(samples) < MAX_REJECTION_SAMPLES_PER_BATCH:
                        samples.append(compact[:180])

                    candidates = _extract_rejection_slug_candidates(raw_output)
                    if candidates:
                        rejected_slug_candidates.update(candidates)
                    else:
                        rejection_events.append(
                            {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "reason": reason,
                                "title": title[:200],
                                "raw_output": compact[:500],
                            }
                        )
                else:
                    rejection_events.append(
                        {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "reason": reason,
                            "title": title[:200],
                            "raw_output": "",
                        }
                    )

        success_count = sum(1 for category, _reason in results if category is not None)
        logger.info(f"Batch classification complete: {success_count}/{len(jobs)} successful")
        if rejection_reasons:
            details = ", ".join(f"{k}={v}" for k, v in sorted(rejection_reasons.items()))
            logger.info("Batch classification rejections: %s", details)
            for reason, samples in rejection_samples.items():
                if not samples:
                    continue
                logger.info("Batch rejection samples (%s): %s", reason, " | ".join(samples))

        if rejected_slug_candidates:
            added = _write_unmapped_categories(rejected_slug_candidates)
            logger.info(
                "Persisted %d rejected slug candidates (%d new)",
                len(rejected_slug_candidates),
                added,
            )

        if rejection_events:
            _append_rejection_events(rejection_events)
            logger.info("Persisted %d non-tokenizable rejection events", len(rejection_events))

        return results

    async def classify_batch(self, jobs: list[tuple[str, str]]) -> list[str | None]:
        """Classify multiple jobs and return categories only."""
        results = await self.classify_batch_with_reasons(jobs)
        return [category for category, _reason in results]

    async def classify_batch_with_progress(
        self,
        jobs: list[tuple[str, str]],
        progress_callback: Any | None = None,
    ) -> list[str | None]:
        """Classify multiple jobs with optional progress callback."""
        return await self.classify_batch(jobs)


# Singleton instance
_classifier_instance: JobClassifier | None = None
_classifier_close_task: asyncio.Task[None] | None = None


def get_classifier() -> JobClassifier:
    """Get or create the job classifier instance."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = JobClassifier()
    return _classifier_instance


def reset_classifier() -> None:
    """Reset the classifier singleton (useful for testing)."""
    global _classifier_instance
    global _classifier_close_task
    if _classifier_instance:
        _classifier_close_task = asyncio.create_task(_classifier_instance.close())
    _classifier_instance = None
