"""Tests for safe public-job cache invalidation diagnostics."""

from __future__ import annotations

import logging

import pytest

from internnexus_core.job_cache import invalidate_public_job_cache


@pytest.mark.asyncio
async def test_missing_invalidation_config_names_only_missing_settings(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        await invalidate_public_job_cache(["job-1"], frontend_internal_url="", secret="")

    assert "FRONTEND_INTERNAL_URL" in caplog.text
    assert "JOB_CACHE_REVALIDATION_SECRET" in caplog.text
