from unittest.mock import AsyncMock

import pytest

from app.services.jobs.sanitize import MAX_DESCRIPTION_BYTES, sanitize_description, sanitize_description_cached


def test_sanitize_removes_unsafe_markup_and_normalizes_links():
    html, truncated = sanitize_description(
        '<h1>ignored</h1><p style="color:red" onclick="bad()">safe</p>'
        '<a href="javascript:alert(1)">bad</a><a href="https://example.com">good</a><script>alert(1)</script>'
    )
    assert truncated is False
    assert "<h1" not in html
    assert "style=" not in html and "onclick=" not in html and "script" not in html
    assert "javascript:" not in html
    assert 'rel="nofollow noopener noreferrer"' in html
    assert 'href="https://example.com"' in html


def test_sanitize_truncates_on_utf8_boundary_before_parsing():
    source = "<p>" + ("é" * MAX_DESCRIPTION_BYTES) + "</p>"
    html, truncated = sanitize_description(source)
    assert truncated is True
    assert "�" not in html
    assert "<script" not in html


@pytest.mark.asyncio
async def test_sanitize_cache_returns_existing_value_without_resanitizing():
    cache = AsyncMock()
    cache.get.return_value = {"html": "<p>cached</p>", "truncated": False}
    assert await sanitize_description_cached("<script>ignored</script>", cache) == ("<p>cached</p>", False)
    cache.set.assert_not_awaited()
