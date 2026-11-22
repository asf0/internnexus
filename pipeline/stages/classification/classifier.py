"""LLM-based job classification service orchestrator."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from pipeline.stages.classification.llm_client import ClassificationClient
from pipeline.stages.classification.response_parser import (  # noqa: F401  # re-exported for existing tests
    _extract_batch_categories,
    _extract_canonical_category,
    _map_category_strict,
    _normalize_slug_token,
)
from pipeline.stages.classification.rejections import (
    MAX_REJECTION_SAMPLES_PER_BATCH,
    _append_rejection_events,
    _extract_rejection_slug_candidates,
    _get_rejection_log_path,  # noqa: F401  # re-exported for existing tests
    _rotate_rejection_logs,  # noqa: F401  # re-exported for existing tests
    _write_unmapped_categories,
)
from pipeline.infra.singletons import SingletonManager
from pipeline.infra.settings import get_settings

logger = logging.getLogger(__name__)


class _RejectionTracker:
    """Accumulate classification rejections for batch-level logging and persistence."""

    def __init__(self) -> None:
        self.reasons: dict[str, int] = {}
        self.samples: dict[str, list[str]] = {}
        self.slug_candidates: set[str] = set()
        self.events: list[dict[str, str]] = []

    def record(self, *, reason: str, title: str, raw_output: str) -> None:
        self.reasons[reason] = self.reasons.get(reason, 0) + 1
        if not raw_output:
            self._add_event(reason, title, "")
            return

        compact = " ".join(raw_output.strip().split())
        samples = self.samples.setdefault(reason, [])
        if len(samples) < MAX_REJECTION_SAMPLES_PER_BATCH:
            samples.append(compact[:180])

        candidates = _extract_rejection_slug_candidates(raw_output)
        if candidates:
            self.slug_candidates.update(candidates)
        else:
            self._add_event(reason, title, compact[:500])

    def _add_event(self, reason: str, title: str, raw_output: str) -> None:
        self.events.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": reason,
                "title": title[:200],
                "raw_output": raw_output,
            }
        )

    def log_and_persist(self) -> None:
        if self.reasons:
            details = ", ".join(f"{k}={v}" for k, v in sorted(self.reasons.items()))
            logger.info("Batch classification rejections: %s", details)
            for reason, samples in self.samples.items():
                if not samples:
                    continue
                logger.info("Batch rejection samples (%s): %s", reason, " | ".join(samples))

        if self.slug_candidates:
            added = _write_unmapped_categories(self.slug_candidates)
            logger.info(
                "Persisted %d rejected slug candidates (%d new)",
                len(self.slug_candidates),
                added,
            )

        if self.events:
            _append_rejection_events(self.events)
            logger.info("Persisted %d non-tokenizable rejection events", len(self.events))


class JobClassifier:
    """Async job classification service using an OpenAI-compatible API."""

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        max_concurrent: int | None = None,
    ) -> None:
        """Initialize the classifier.

        Args:
            model: Model name (defaults to settings.classification_model)
            base_url: API URL (defaults to settings.openai_base_url)
            timeout: Request timeout in seconds
            max_concurrent: Maximum concurrent requests for batch processing
        """
        settings = get_settings()
        self._client = ClassificationClient(
            model=model,
            base_url=base_url,
            timeout=timeout,
            max_concurrent=max_concurrent,
            settings=settings,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.close()

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
            except Exception:  # noqa: BLE001  # per-job fallback: one failed job should not stop the rest
                logger.exception("Error classifying job '%s'", title)
                results.append((None, "unexpected_error", ""))
        return results

    async def _classify_chunk_with_fallback(
        self, chunk: list[tuple[str, str]], batch_size: int
    ) -> list[tuple[str | None, str, str]]:
        """Classify one prompt batch, falling back to per-job classification."""
        try:
            if len(chunk) == 1 or batch_size == 1:
                return await self.classify_batch_individually_with_reasons(chunk)
            chunk_results = await self._client.classify_prompt_batch_with_reasons(chunk)
            if any(
                reason in {"invalid_json", "invalid_json_shape"}
                for _category, reason, _raw in chunk_results
            ):
                logger.warning(
                    "Batch classification response was not parseable for %d jobs; retrying individually",
                    len(chunk),
                )
                return await self.classify_batch_individually_with_reasons(chunk)
            return chunk_results
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001  # batch failure falls back to individual classification
            logger.warning(
                "Batch classification failed for %d jobs; retrying individually: %s",
                len(chunk),
                exc,
            )
            return await self.classify_batch_individually_with_reasons(chunk)

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
                chunk_results = await self._classify_chunk_with_fallback(chunk, batch_size)

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
        tracker = _RejectionTracker()
        for idx, result, reason, raw_output in results_with_idx:
            results[idx] = (result, reason)
            if result is None:
                tracker.record(reason=reason, title=jobs[idx][0], raw_output=raw_output)

        success_count = sum(1 for category, _reason in results if category is not None)
        logger.info(
            "Batch classification complete: %d/%d successful (prompt_batch_size=%d)",
            success_count,
            len(jobs),
            batch_size,
        )
        tracker.log_and_persist()

        return results


_classifier = SingletonManager(
    factory=JobClassifier,
    aclose=lambda classifier: classifier.close(),
)


def get_classifier() -> JobClassifier:
    """Get or create the job classifier instance."""
    return _classifier.get()


async def reset_classifier_async() -> None:
    """Reset the classifier singleton and await close (for cleanup)."""
    await _classifier.aclose()
