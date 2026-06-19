"""Retry helper for transient PostgreSQL concurrency errors.

Catches SQLAlchemy DBAPIError, inspects the exception chain for retryable
SQLSTATE codes (deadlock, serialization, lock-not-available), rolls back the
session, and retries with jittered exponential backoff.
"""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.exc import DBAPIError

logger = logging.getLogger(__name__)

# 40P01 deadlock_detected, 40001 serialization_failure, 55P03 lock_not_available
RETRYABLE_SQLSTATES = frozenset({"40P01", "40001", "55P03"})

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BASE_DELAY = 0.5
DEFAULT_MAX_DELAY = 4.0


def _retryable_sqlstate(exc: BaseException) -> str | None:
    """Walk the exception chain and return the first retryable SQLSTATE, if any.

    SQLAlchemy wraps the driver exception in DBAPIError; the original driver
    error is accessible via ``exc.orig``. We also walk ``__cause__`` and
    ``__context__`` to be robust to nested wrapping.
    """
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        for attr in ("pgcode", "sqlstate", "code"):
            code = getattr(current, attr, None)
            if isinstance(code, str) and code in RETRYABLE_SQLSTATES:
                return code
        current = (
            getattr(current, "orig", None)
            or current.__cause__
            or current.__context__
        )
    return None


async def with_db_retry(
    func: Callable[[], Awaitable[Any]],
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    rollback: Callable[[], Awaitable[Any]] | None = None,
) -> Any:
    """Execute *func* with retry on transient PostgreSQL concurrency errors.

    Args:
        func: Zero-arg async callable producing the result.
        max_attempts: Maximum number of attempts (including the first).
        base_delay: Base delay in seconds for the first retry.
        max_delay: Upper bound on the per-retry delay.
        rollback: Optional async callback to roll back the session before
            retrying. Rollback errors are logged and swallowed so they never
            mask the original retryable error.

    Returns:
        The result of *func*.

    Raises:
        The last exception if all attempts are exhausted or the error is not
        retryable.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return await func()
        except DBAPIError as exc:
            code = _retryable_sqlstate(exc)
            if code is None or attempt >= max_attempts:
                raise
            if rollback is not None:
                try:
                    await rollback()
                except Exception:  # noqa: BLE001  # rollback must not mask the retryable error
                    logger.warning("Rollback failed before retry", exc_info=True)
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            delay *= 0.5 + random.random()
            logger.warning(
                "Retryable DB error %s on attempt %d/%d, retrying in %.2fs",
                code,
                attempt,
                max_attempts,
                delay,
            )
            await asyncio.sleep(delay)
