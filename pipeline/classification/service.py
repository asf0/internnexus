"""LLM-based job classification service orchestrator."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from pipeline.classification.client import ClassificationClient
from pipeline.classification.parser import (  # noqa: F401  # re-exported for existing tests
    _extract_batch_categories,
    _extract_canonical_category,
    _map_category_strict,
    _normalize_slug_token,
)
from pipeline.classification.rejections import (
    MAX_REJECTION_SAMPLES_PER_BATCH,
    _append_rejection_events,
    _extract_rejection_slug_candidates,
    _get_rejection_log_path,  # noqa: F401  # re-exported for existing tests
    _rotate_rejection_logs,  # noqa: F401  # re-exported for existing tests
    _write_unmapped_categories,
)
from pipeline.config import get_settings

logger = logging.getLogger(__name__)


class JobClassifier:
    """Async job classification service supporting Ollama and OpenAI-compatible APIs."""

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
            base_url: API URL (defaults to settings.openai_base_url)
            provider: "ollama" or "openai-compatible" (defaults to settings.embedding_provider)
            timeout: Request timeout in seconds
            max_concurrent: Maximum concurrent requests for batch processing
        """
        settings = get_settings()
        self._client = ClassificationClient(
            model=model,
            base_url=base_url,
            provider=provider,
            timeout=timeout,
            max_concurrent=max_concurrent,
            settings=settings,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.close()

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
        return await self._client.classify_job_with_reason(title, description)

    async def classify_batch_individually_with_reasons(
        self,
        jobs: list[tuple[str, str]],
    ) -> list[tuple[str | None, str, str]]:
        """Classify each job individually; used as fallback path."""
        results: list[tuple[str | None, str, str]] = []
        for title, description in jobs:
            try:
                results.append(await self._classify_job_with_reason(title, description))
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001  # per-job fallback: one failed job should not stop the rest
                logger.error("Error classifying job '%s': %s", title, exc)
                results.append((None, "unexpected_error", ""))
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

    async def classify_batch_with_reasons(self, jobs: list[tuple[str, str]]) -> list[tuple[str | None, str]]:
        """Classify multiple jobs using true prompt batching with fallback.

        Args:
            jobs: List of (title, description) tuples

        Returns:
            List of (category slug or None, reason) in input order
        """
        if not jobs:
            return []

        batch_size = max(1, min(self._client.batch_size, len(jobs)))
        semaphore = asyncio.Semaphore(self._client.max_concurrent)
        completed = 0
        lock = asyncio.Lock()

        async def classify_chunk(
            start_index: int,
            chunk: list[tuple[str, str]],
        ) -> list[tuple[int, str | None, str, str]]:
            nonlocal completed
            async with semaphore:
                try:
                    if len(chunk) == 1 or batch_size == 1:
                        chunk_results = await self.classify_batch_individually_with_reasons(chunk)
                    else:
                        chunk_results = await self._client.classify_prompt_batch_with_reasons(chunk)
                        if any(
                            reason in {"invalid_json", "invalid_json_shape"}
                            for _category, reason, _raw in chunk_results
                        ):
                            logger.warning(
                                "Batch classification response was not parseable for %d jobs; retrying individually",
                                len(chunk),
                            )
                            chunk_results = await self.classify_batch_individually_with_reasons(chunk)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001  # batch failure falls back to individual classification
                    logger.warning(
                        "Batch classification failed for %d jobs; retrying individually: %s",
                        len(chunk),
                        exc,
                    )
                    chunk_results = await self.classify_batch_individually_with_reasons(chunk)

                async with lock:
                    completed += len(chunk)
                    if completed % 50 == 0 or completed == len(jobs):
                        logger.info("Classification progress: %d/%d", completed, len(jobs))

                return [
                    (start_index + offset, category, reason, raw_output)
                    for offset, (category, reason, raw_output) in enumerate(chunk_results)
                ]

        tasks = [
            classify_chunk(start_index, jobs[start_index : start_index + batch_size])
            for start_index in range(0, len(jobs), batch_size)
        ]

        try:
            chunked_results = await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.warning("Batch classification cancelled")
            raise

        results_with_idx = [item for chunk in chunked_results for item in chunk]
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
        logger.info(
            "Batch classification complete: %d/%d successful (prompt_batch_size=%d)",
            success_count,
            len(jobs),
            batch_size,
        )
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


async def reset_classifier_async() -> None:
    """Reset the classifier singleton and await close (for cleanup)."""
    global _classifier_instance, _classifier_close_task
    if _classifier_instance:
        await _classifier_instance.close()
    _classifier_instance = None
    _classifier_close_task = None
