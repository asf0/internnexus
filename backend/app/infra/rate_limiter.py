from __future__ import annotations

import ipaddress
from functools import lru_cache

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.infra.config import get_settings


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


@lru_cache
def _get_trusted_proxy_networks() -> (
    list[ipaddress.IPv4Network | ipaddress.IPv6Network]
):
    settings = get_settings()
    return _parse_networks(settings.trusted_proxy_ips)


def _request_source_ip(request) -> str:
    return _parse_ip(get_remote_address(request)) or "127.0.0.1"


def _should_trust_proxy_headers(request) -> bool:
    """Only trust forwarded headers if explicitly enabled.

    If TRUSTED_PROXY_IPS is set, only direct source IPs in that allowlist are trusted.
    """
    settings = get_settings()
    if not settings.trust_proxy_headers:
        return False
    networks = _get_trusted_proxy_networks()
    if not networks:
        return True
    source_ip = ipaddress.ip_address(_request_source_ip(request))
    return any(source_ip in network for network in networks)


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


def _build_limiter() -> Limiter:
    settings = get_settings()
    if settings.redis_url:
        return Limiter(key_func=get_real_client_ip, storage_uri=settings.redis_url)
    return Limiter(key_func=get_real_client_ip)


_PER_MINUTE_60 = "60/minute"
_PER_MINUTE_30 = "30/minute"
_PER_MINUTE_20 = "20/minute"
_PER_MINUTE_5 = "5/minute"

RATE_LIMITS = {
    "match": _PER_MINUTE_60,
    "jobs_list": _PER_MINUTE_60,
    "jobs_detail": _PER_MINUTE_60,
    "filters": _PER_MINUTE_30,
    # A daily revalidation generates one chunk per 50k jobs (about 15 for the
    # current catalogue) in a burst; 10/minute rejected the later chunks with
    # 429s, leaving the sitemap partially generated. The limit still stops a
    # multi-megabyte response from being hammered.
    "sitemap": _PER_MINUTE_60,
    "health": "1000/minute",
    "auth_register": _PER_MINUTE_5,
    "auth_login": "10/minute",
    "auth_oauth": _PER_MINUTE_20,
    "auth_set_credential": _PER_MINUTE_5,
    "user_me": _PER_MINUTE_60,
    "user_update": _PER_MINUTE_20,
    "user_delete": "5/hour",
    "job_click": _PER_MINUTE_30,
    "admin": _PER_MINUTE_30,
    "admin_read": _PER_MINUTE_60,
    "admin_write": _PER_MINUTE_20,
    "admin_destructive": _PER_MINUTE_5,
    "admin_bulk": "3/minute",
}
limiter = _build_limiter()
