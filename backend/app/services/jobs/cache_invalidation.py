"""Best-effort invalidation for public job-detail pages."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from internnexus_core.job_cache import invalidate_public_job_cache

from app.infra.config import get_settings


async def invalidate_job_detail_cache(job_ids: Iterable[UUID]) -> None:
    settings = get_settings()
    await invalidate_public_job_cache(
        job_ids,
        frontend_internal_url=settings.frontend_internal_url,
        secret=settings.job_cache_revalidation_secret,
    )
