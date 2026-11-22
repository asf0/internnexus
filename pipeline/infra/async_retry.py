"""Shared retry policy, delay calculation, and async execution."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Configuration for bounded exponential retries."""

    max_attempts: int
    base_delay: float
    max_delay: float
    jitter_max: float = 0.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.base_delay < 0:
            raise ValueError("base_delay must be non-negative")
        if self.max_delay < 0:
            raise ValueError("max_delay must be non-negative")
        if self.jitter_max < 0:
            raise ValueError("jitter_max must be non-negative")


def delay_for_attempt(
    policy: RetryPolicy,
    attempt: int,
    *,
    provider_retry_after: float | None = None,
    random_value: Callable[[], float] | None = None,
) -> float:
    """Calculate max(exponential, provider delay) plus bounded jitter."""
    if attempt < 1:
        raise ValueError("attempt must be at least 1")
    exponential = min(
        policy.max_delay,
        policy.base_delay * (2 ** (attempt - 1)),
    )
    provider_delay = max(0.0, provider_retry_after or 0.0)
    jitter_source = random_value or random.random
    return max(exponential, provider_delay) + (jitter_source() * policy.jitter_max)


async def with_retry[T](
    op: Callable[[], Awaitable[T]],
    *,
    policy: RetryPolicy,
    retryable: Callable[[BaseException], bool],
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    retry_after: Callable[[BaseException], float | None] | None = None,
    random_value: Callable[[], float] | None = None,
    before_sleep: Callable[[BaseException, int, float], None] | None = None,
) -> T:
    """Run an async operation using a bounded retry policy."""
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return await op()
        except asyncio.CancelledError:
            raise
        except BaseException as exc:
            if attempt >= policy.max_attempts or not retryable(exc):
                raise
            delay = delay_for_attempt(
                policy,
                attempt,
                provider_retry_after=retry_after(exc) if retry_after else None,
                random_value=random_value,
            )
            if before_sleep is not None:
                before_sleep(exc, attempt, delay)
            await sleep(delay)

    raise RuntimeError("retry loop completed without returning or raising")
