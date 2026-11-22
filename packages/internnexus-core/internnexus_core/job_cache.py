"""Best-effort invalidation for the frontend's public job-detail Data Cache."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)

MAX_INVALIDATION_BATCH_SIZE = 100


async def invalidate_public_job_cache(
    job_ids: Iterable[UUID | str],
    *,
    frontend_internal_url: str,
    secret: str,
) -> None:
    """Ask Next.js to revalidate changed public job entries after a DB commit.

    This must never make an already-committed write fail. The frontend's 30
    minute TTL is the fallback if the internal request is unavailable.
    """
    unique_ids = list(dict.fromkeys(str(job_id) for job_id in job_ids))
    if not unique_ids:
        return
    if not frontend_internal_url or not secret:
        missing = []
        if not frontend_internal_url:
            missing.append("FRONTEND_INTERNAL_URL")
        if not secret:
            missing.append("JOB_CACHE_REVALIDATION_SECRET")
        logger.warning(
            "Job cache invalidation is not configured (missing: %s); relying on TTL",
            ", ".join(missing),
        )
        return

    endpoint = frontend_internal_url.rstrip("/") + "/api/internal/job-cache/revalidate"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            for start in range(0, len(unique_ids), MAX_INVALIDATION_BATCH_SIZE):
                response = await client.post(
                    endpoint,
                    json={"job_ids": unique_ids[start : start + MAX_INVALIDATION_BATCH_SIZE]},
                    headers={"Authorization": f"Bearer {secret}"},
                )
                response.raise_for_status()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Job cache invalidation failed; relying on TTL: %s", exc)
