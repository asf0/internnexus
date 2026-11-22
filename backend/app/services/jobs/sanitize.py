"""Safe, bounded rendering of scraped job descriptions."""

from __future__ import annotations

import hashlib

import nh3

from app.infra.cache.cache_service import CacheService
from app.infra.benchmark_counters import record

MAX_DESCRIPTION_BYTES = 256 * 1024
_TAGS = {"p", "ul", "ol", "li", "strong", "em", "b", "i", "br", "h2", "h3", "h4", "h5", "h6", "a", "blockquote", "code", "pre"}
_ATTRIBUTES = {"a": {"href", "title"}}


def _truncate_utf8(value: str) -> tuple[str, bool]:
    encoded = value.encode("utf-8")
    if len(encoded) <= MAX_DESCRIPTION_BYTES:
        return value, False
    return encoded[:MAX_DESCRIPTION_BYTES].decode("utf-8", errors="ignore"), True


def sanitize_description(value: str) -> tuple[str, bool]:
    """Return safe HTML and whether the raw value exceeded the serving cap."""
    bounded, was_truncated = _truncate_utf8(value)
    return (
        nh3.clean(
            bounded,
            tags=_TAGS,
            attributes=_ATTRIBUTES,
            url_schemes={"https", "http", "mailto"},
            link_rel="nofollow noopener noreferrer",
        ),
        was_truncated,
    )


async def sanitize_description_cached(value: str, cache: CacheService) -> tuple[str, bool]:
    """Reuse the shared bounded cache for repeat descriptions across re-scrapes."""
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]
    key = f"jobsan:v1:{digest}"
    cached = await cache.get(key)
    if isinstance(cached, dict) and isinstance(cached.get("html"), str):
        record("job_detail_sanitizer_cache_hits")
        return cached["html"], bool(cached.get("truncated", False))
    record("job_detail_sanitizer_executions")
    html, was_truncated = sanitize_description(value)
    await cache.set(key, {"html": html, "truncated": was_truncated}, ttl=86400)
    return html, was_truncated
