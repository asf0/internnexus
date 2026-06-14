"""Unit tests for core HTTP client builder."""

from __future__ import annotations

import pytest


class TestHttpClientDefaults:
    """Test HTTP client configuration defaults."""

    def test_get_http_client_returns_async_client(self):
        from internnexus_core.http_client import get_http_client
        import httpx

        client = get_http_client()
        assert isinstance(client, httpx.AsyncClient)

    def test_get_http_client_timeout_defaults(self):
        from internnexus_core.http_client import get_http_client

        client = get_http_client()
        assert client.timeout.connect == 10.0
        assert client.timeout.read == 30.0
        assert client.timeout.write == 30.0
        assert client.timeout.pool == 30.0

    def test_get_http_client_connection_limits(self):
        from internnexus_core import http_client as http_client_mod
        import inspect

        source = inspect.getsource(http_client_mod)
        assert "max_connections=100" in source
        assert "max_keepalive_connections=20" in source

    def test_get_http_client_is_singleton(self):
        from internnexus_core.http_client import get_http_client

        client_a = get_http_client()
        client_b = get_http_client()
        assert client_a is client_b

    @pytest.mark.asyncio
    async def test_close_http_client_resets_singleton(self):
        from internnexus_core.http_client import get_http_client, close_http_client

        client = get_http_client()
        assert client is not None

        await close_http_client()

        # After close, the singleton is reset — next call creates a new client
        from internnexus_core import http_client as http_client_mod
        assert http_client_mod._http_client is None

    @pytest.mark.asyncio
    async def test_close_http_client_is_idempotent(self):
        from internnexus_core.http_client import close_http_client

        await close_http_client()
        await close_http_client()
