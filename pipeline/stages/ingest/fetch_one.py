"""Shared per-slug fetch helper with 404 cooldown handling.

Used by the concurrent source stream (``source_stream.fetch_source_jobs_streamed``).

This module is a dependency leaf: it must not import the orchestration modules
(``fetch_all``, ``source_stream``, ``board_processing``) or the extraction would
introduce an import cycle.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import NotRequired, TypedDict

import httpx

from pipeline.domain import JobSchema

logger = logging.getLogger(__name__)


class SlugFetchError(TypedDict):
    step: str
    source: str
    slug: str
    error_type: str
    run_id: NotRequired[str | None]
    status_code: NotRequired[int | None]
    message: NotRequired[str]
    cooldown_until: NotRequired[float]


async def fetch_one(
    *,
    slug: str,
    fetch_func: Callable[[str], list[JobSchema]],
    semaphore: asyncio.Semaphore,
    source_name: str,
    source_404_cache: dict[str, float],
    cache_lock: asyncio.Lock,
    cooldown_hours: int,
    run_id: str | None,
) -> tuple[list[JobSchema], SlugFetchError | None]:
    """Bounded-to-thread fetch of one slug with 404 cooldown handling.

    An empty successful source returns ``([], None)``. The first 404 records
    ``http_404`` and a positive cooldown timestamp, which makes the source
    incomplete for deletion safety. A later 404 after that cooldown records
    ``http_404_confirmed`` and stores the negated expiry as a compact retired
    marker; confirmed retired slugs no longer poison cleanup for other
    companies. Any successful recheck clears the marker.
    """
    async with semaphore:
        try:
            jobs = await asyncio.to_thread(fetch_func, slug)
            async with cache_lock:
                source_404_cache.pop(slug, None)
            return jobs, None
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response is not None else 0
            if status_code == 404:
                cooldown_until = time.time() + (max(1, cooldown_hours) * 3600)
                async with cache_lock:
                    confirmed = slug in source_404_cache
                    source_404_cache[slug] = -cooldown_until if confirmed else cooldown_until
                logger.info(
                    "%s slug '%s' returned %s 404; skipping for %dh",
                    source_name,
                    slug,
                    "confirmed" if confirmed else "first",
                    max(1, cooldown_hours),
                )
                return [], {
                    "step": "ingest",
                    "source": source_name.lower(),
                    "slug": slug,
                    "run_id": run_id,
                    "error_type": "http_404_confirmed" if confirmed else "http_404",
                    "status_code": 404,
                    "message": str(exc),
                    "cooldown_until": cooldown_until,
                }
            return [], {
                "step": "ingest",
                "source": source_name.lower(),
                "slug": slug,
                "run_id": run_id,
                "error_type": "http_error",
                "status_code": status_code,
                "message": str(exc),
            }
        except Exception as exc:  # noqa: BLE001  # catch-all to record per-slug failure without crashing ingest
            return [], {
                "step": "ingest",
                "source": source_name.lower(),
                "slug": slug,
                "run_id": run_id,
                "error_type": "exception",
                "status_code": None,
                "message": str(exc),
            }
