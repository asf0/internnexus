"""Tests for shared async retry behavior."""

from __future__ import annotations

import asyncio

import pytest

from pipeline.infra.async_retry import RetryPolicy, delay_for_attempt, with_retry


def test_delay_for_attempt_is_bounded_and_adds_injected_jitter() -> None:
    policy = RetryPolicy(
        max_attempts=4,
        base_delay=2,
        max_delay=5,
        jitter_max=0.5,
    )

    assert delay_for_attempt(policy, 1, random_value=lambda: 0.5) == 2.25
    assert delay_for_attempt(policy, 2, random_value=lambda: 0.5) == 4.25
    assert delay_for_attempt(policy, 3, random_value=lambda: 0.5) == 5.25


@pytest.mark.asyncio
async def test_with_retry_returns_without_sleep_on_success() -> None:
    sleeps: list[float] = []

    async def sleep(delay: float) -> None:
        sleeps.append(delay)

    async def op() -> str:
        return "ok"

    result = await with_retry(
        op,
        policy=RetryPolicy(3, 1, 10),
        retryable=lambda _exc: True,
        sleep=sleep,
    )

    assert result == "ok"
    assert sleeps == []


@pytest.mark.asyncio
async def test_with_retry_retries_then_succeeds() -> None:
    attempts = 0
    sleeps: list[float] = []
    callbacks: list[tuple[int, float]] = []

    async def op() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("temporary")
        return "ok"

    async def sleep(delay: float) -> None:
        sleeps.append(delay)

    result = await with_retry(
        op,
        policy=RetryPolicy(3, 1, 10),
        retryable=lambda exc: isinstance(exc, RuntimeError),
        sleep=sleep,
        before_sleep=lambda _exc, attempt, delay: callbacks.append((attempt, delay)),
    )

    assert result == "ok"
    assert attempts == 3
    assert sleeps == [1, 2]
    assert callbacks == [(1, 1), (2, 2)]


@pytest.mark.asyncio
async def test_with_retry_raises_non_retryable_immediately() -> None:
    attempts = 0

    async def op() -> None:
        nonlocal attempts
        attempts += 1
        raise ValueError("permanent")

    with pytest.raises(ValueError, match="permanent"):
        await with_retry(
            op,
            policy=RetryPolicy(3, 1, 10),
            retryable=lambda exc: isinstance(exc, RuntimeError),
        )

    assert attempts == 1


@pytest.mark.asyncio
async def test_with_retry_raises_after_max_attempts() -> None:
    attempts = 0
    sleeps: list[float] = []

    async def op() -> None:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("temporary")

    async def sleep(delay: float) -> None:
        sleeps.append(delay)

    with pytest.raises(RuntimeError, match="temporary"):
        await with_retry(
            op,
            policy=RetryPolicy(3, 1, 10),
            retryable=lambda _exc: True,
            sleep=sleep,
        )

    assert attempts == 3
    assert sleeps == [1, 2]


@pytest.mark.asyncio
async def test_with_retry_never_retries_cancellation() -> None:
    sleeps: list[float] = []

    async def op() -> None:
        raise asyncio.CancelledError

    async def sleep(delay: float) -> None:
        sleeps.append(delay)

    with pytest.raises(asyncio.CancelledError):
        await with_retry(
            op,
            policy=RetryPolicy(3, 1, 10),
            retryable=lambda _exc: True,
            sleep=sleep,
        )

    assert sleeps == []


def test_delay_honors_long_provider_retry_after_before_jitter() -> None:
    policy = RetryPolicy(max_attempts=3, base_delay=1, max_delay=5, jitter_max=0.5)

    delay = delay_for_attempt(
        policy,
        4,
        provider_retry_after=20,
        random_value=lambda: 0.5,
    )

    assert delay == 20.25
