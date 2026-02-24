from __future__ import annotations

import ipaddress
from types import SimpleNamespace

from app import rate_limiter


def _request(
    *,
    remote_ip: str,
    headers: dict[str, str] | None = None,
):
    return SimpleNamespace(
        headers=headers or {},
        client=SimpleNamespace(host=remote_ip),
    )


def test_untrusted_proxy_ignores_forwarded_headers(monkeypatch):
    monkeypatch.setattr(rate_limiter, "_TRUST_PROXY_HEADERS", False)
    monkeypatch.setattr(rate_limiter, "_TRUSTED_PROXY_NETWORKS", [])
    monkeypatch.setattr(rate_limiter, "get_remote_address", lambda request: request.client.host)

    request = _request(
        remote_ip="203.0.113.10",
        headers={
            "CF-Connecting-IP": "198.51.100.8",
            "X-Forwarded-For": "198.51.100.7",
        },
    )

    assert rate_limiter.get_real_client_ip(request) == "203.0.113.10"


def test_trusted_proxy_prefers_cf_connecting_ip(monkeypatch):
    monkeypatch.setattr(rate_limiter, "_TRUST_PROXY_HEADERS", True)
    monkeypatch.setattr(rate_limiter, "_TRUSTED_PROXY_NETWORKS", [])
    monkeypatch.setattr(rate_limiter, "get_remote_address", lambda request: request.client.host)

    request = _request(
        remote_ip="10.0.0.5",
        headers={
            "CF-Connecting-IP": "198.51.100.9",
            "X-Forwarded-For": "203.0.113.33",
        },
    )

    assert rate_limiter.get_real_client_ip(request) == "198.51.100.9"


def test_trusted_proxy_with_allowlist_rejects_untrusted_source(monkeypatch):
    monkeypatch.setattr(rate_limiter, "_TRUST_PROXY_HEADERS", True)
    monkeypatch.setattr(
        rate_limiter,
        "_TRUSTED_PROXY_NETWORKS",
        [ipaddress.ip_network("10.0.0.0/8")],
    )
    monkeypatch.setattr(rate_limiter, "get_remote_address", lambda request: request.client.host)

    request = _request(
        remote_ip="192.168.1.10",
        headers={"X-Forwarded-For": "198.51.100.99"},
    )

    assert rate_limiter.get_real_client_ip(request) == "192.168.1.10"


def test_x_forwarded_for_uses_first_valid_ip(monkeypatch):
    monkeypatch.setattr(rate_limiter, "_TRUST_PROXY_HEADERS", True)
    monkeypatch.setattr(rate_limiter, "_TRUSTED_PROXY_NETWORKS", [])
    monkeypatch.setattr(rate_limiter, "get_remote_address", lambda request: request.client.host)

    request = _request(
        remote_ip="10.0.0.5",
        headers={"X-Forwarded-For": "unknown, 203.0.113.44, 198.51.100.77"},
    )

    assert rate_limiter.get_real_client_ip(request) == "203.0.113.44"
