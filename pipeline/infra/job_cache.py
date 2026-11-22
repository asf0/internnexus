"""Best-effort frontend cache invalidation after committed pipeline writes."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from internnexus_core.job_cache import invalidate_public_job_cache
from pipeline.infra.settings import get_settings


async def invalidate_job_detail_cache(job_ids: Iterable[UUID]) -> None:
    settings = get_settings()
    await invalidate_public_job_cache(
        job_ids,
        frontend_internal_url=settings.frontend_internal_url,
        secret=settings.job_cache_revalidation_secret,
    )
