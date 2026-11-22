"""Shared synchronous HTTP plumbing for ATS source adapters."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, Self

import httpx
from tenacity import Retrying, retry_if_exception, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


def is_retryable_ats_error(exc: BaseException) -> bool:
    """Return whether an ATS request failure is safe to retry."""
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return False


class BaseATSClient:
    """Lifecycle and retry policy shared by synchronous ATS adapters.

    A client instance owns one HTTPX connection pool for the duration of a
    source run. Requests retry at most three times for transient transport,
    rate-limit, and server failures; other client errors surface immediately.
    """

    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        self.close()

    def _get_json(self, url: str, params: Mapping[str, Any] | None = None) -> Any:
        def request_json() -> Any:
            response = self._client.get(url, params=params)
            response.raise_for_status()
            return response.json()

        def log_retry(retry_state) -> None:
            logger.debug(
                "Retrying ATS request to %s after %s (attempt %d)",
                url,
                retry_state.outcome.exception() if retry_state.outcome else "unknown error",
                retry_state.attempt_number,
            )

        return Retrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
            retry=retry_if_exception(is_retryable_ats_error),
            before_sleep=log_retry,
            reraise=True,
        )(request_json)
