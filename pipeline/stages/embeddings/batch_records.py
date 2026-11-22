"""Typed records and failure classification for the embedding stage.

Using ``NamedTuple`` keeps the existing tuple unpacking and indexing at call
sites while giving the batch and retry payloads named fields.
"""

from __future__ import annotations

import asyncio
from typing import NamedTuple
from uuid import UUID

from internnexus_core.embedding import EmbeddingError, RateLimitError


class RetryItem(NamedTuple):
    """One failed job queued for a later embedding retry round."""

    job_id: UUID
    error_type: str
    message: str
    attempt: int


class BatchResult(NamedTuple):
    """Outcome of processing one batch: (success, errors, skipped, failed)."""

    success: int
    errors: int
    skipped: int
    failed: list[tuple[UUID, BaseException]]


def classify_error(error: BaseException) -> tuple[str, bool]:
    """Classify error as (error_type, is_retryable)."""
    if isinstance(error, RateLimitError):
        return "rate_limit", True
    if isinstance(error, EmbeddingError):
        return "embedding_error", error.retryable
    if isinstance(error, asyncio.TimeoutError):
        return "timeout", True
    if isinstance(error, asyncio.CancelledError):
        return "cancelled", False
    return "unknown", True


def classify_failures(
    failed: list[tuple[UUID, BaseException]],
) -> tuple[list[tuple[UUID, str, str]], set[UUID]]:
    """Split failures into retryable ``(job_id, error_type, message)`` items
    and the set of permanently failed job IDs.
    """
    retryable: list[tuple[UUID, str, str]] = []
    permanent: set[UUID] = set()
    for job_id, error in failed:
        error_type, is_retryable = classify_error(error)
        if is_retryable:
            retryable.append((job_id, error_type, str(error)))
        else:
            permanent.add(job_id)
    return retryable, permanent
