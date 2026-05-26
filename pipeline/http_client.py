"""Pipeline HTTP client with connection pooling."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """Get or create the shared HTTP client."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
                keepalive_expiry=30.0,
            ),
        )
        logger.info("HTTP client pool created")
    return _http_client


async def close_http_client() -> None:
    """Close the HTTP client. Call on app shutdown."""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
        logger.info("HTTP client pool closed")
