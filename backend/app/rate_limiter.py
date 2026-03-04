from __future__ import annotations

import ipaddress
import os

from slowapi import Limiter
from slowapi.util import get_remote_address


def _parse_ip(value: str | None) -> str | None:
    """Return canonical IP string, or None if value is invalid."""
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


def _parse_networks(raw: str) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for entry in raw.split(","):
        token = entry.strip()
        if not token:
            continue
        try:
            if "/" in token:
                networks.append(ipaddress.ip_network(token, strict=False))
            else:
                # Interpret a single address as a /32 or /128 network.
                ip = ipaddress.ip_address(token)
                suffix = "/32" if ip.version == 4 else "/128"
                networks.append(ipaddress.ip_network(f"{ip}{suffix}", strict=False))
        except ValueError:
            continue
    return networks


_TRUST_PROXY_HEADERS = os.getenv("TRUST_PROXY_HEADERS", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
_TRUSTED_PROXY_NETWORKS = _parse_networks(os.getenv("TRUSTED_PROXY_IPS", ""))


def _request_source_ip(request) -> str:
    return _parse_ip(get_remote_address(request)) or "127.0.0.1"


def _should_trust_proxy_headers(request) -> bool:
    """Only trust forwarded headers if explicitly enabled.

    If TRUSTED_PROXY_IPS is set, only direct source IPs in that allowlist are trusted.
    """
    if not _TRUST_PROXY_HEADERS:
        return False
    if not _TRUSTED_PROXY_NETWORKS:
        return True
    source_ip = ipaddress.ip_address(_request_source_ip(request))
    return any(source_ip in network for network in _TRUSTED_PROXY_NETWORKS)


def get_real_client_ip(request):
    """Return client IP for rate limiting with proxy-trust safeguards."""
    source_ip = _request_source_ip(request)

    if not _should_trust_proxy_headers(request):
        return source_ip

    cf_ip = _parse_ip(request.headers.get("CF-Connecting-IP"))
    if cf_ip:
        return cf_ip

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        for token in forwarded.split(","):
            parsed = _parse_ip(token)
            if parsed:
                return parsed

    return source_ip


redis_url = os.getenv("REDIS_URL")

RATE_LIMITS = {
    "match": "60/minute",
    "jobs_list": "60/minute",
    "jobs_detail": "60/minute",
    "filters": "30/minute",
    "health": "1000/minute",
    "auth_register": "5/minute",
    "auth_login": "10/minute",
    "auth_oauth": "20/minute",
    "auth_set_password": "5/minute",
    "user_me": "60/minute",
    "user_update": "20/minute",
    "user_delete": "5/hour",
    "job_click": "30/minute",
    "admin": "30/minute",
}
if redis_url:
    limiter = Limiter(key_func=get_real_client_ip, storage_uri=redis_url)
else:
    limiter = Limiter(key_func=get_real_client_ip)
