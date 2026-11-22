"""Jobs API endpoints - refactored to use service layer."""

from __future__ import annotations

from typing import Annotated

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.jobs import (
    JobListResponse,
    JobResponse,
    SitemapJobListResponse,
    SitemapJobResponse,
)
from app.schemas.mappers import enum_to_str, job_to_response
from app.services.jobs.related import RelatedJobsService
from app.auth.dependencies import get_optional_user, security
from app.infra.cache.cache_service import CacheService, get_cache_service
from app.infra.config import get_settings
from app.infra.db import get_db
from app.models import JobClick, SavedJob, User
from app.infra.rate_limiter import RATE_LIMITS, get_real_client_ip, limiter
from app.repositories.job import JobRepository
from app.services.jobs.search import JobSearchParams, JobSearchService
from app.services.jobs.location import LocationService
from app.services.jobs.sanitize import sanitize_description_cached
from app.infra.url import add_utm_params
from app.infra.commit import commit_or_500
from app.infra.benchmark_counters import record, snapshot

router = APIRouter()
_JOB_NOT_FOUND = "Job not found"
MAX_PAGINATION_OFFSET = 100_000
logger = logging.getLogger(__name__)
DbSessionDependency = Annotated[AsyncSession, Depends(get_db)]
OptionalUserDependency = Annotated[User | None, Depends(get_optional_user)]


def _hash_client_ip(client_ip: str) -> str:
    """Create a non-reversible, deployment-keyed pseudonym for click analytics."""
    secret = get_settings().resolved_ip_hash_secret.encode("utf-8")
    payload = f"job-click-ip:v1:{client_ip}".encode("utf-8")
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()[:16]


class ClickRequest(BaseModel):
    """Request body for job click tracking."""

    utm_medium: str | None = Field(default=None, max_length=100)
    utm_campaign: str | None = Field(default=None, max_length=100)


class ClickResponse(BaseModel):
    """Response for job click tracking."""

    apply_url: str
    job_id: str


class JobListQuery(BaseModel):
    """Optional query filters for the public job list."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: str | None = None
    company: str | None = None
    location: str | None = None
    category: str | None = None
    job_type: str | None = None
    work_mode: str | None = None
    posted_within: str | None = None
    match_ids: str | None = None
    saved_only: bool = False

    @model_validator(mode="after")
    def validate_offset(self) -> "JobListQuery":
        if (self.page - 1) * self.page_size > MAX_PAGINATION_OFFSET:
            raise ValueError(f"pagination offset must not exceed {MAX_PAGINATION_OFFSET}")
        return self


# Route handlers depend on the `_..._dependency` wrappers below rather than on
# `get_job_search_service` / `get_cache_service` directly. This indirection is a
# deliberate test seam: the wrappers resolve the underlying factories by name at
# request time, so the test suite can `patch("app.api.jobs.get_job_search_service")`
# / `patch("app.api.jobs.get_cache_service")` and have the override take effect.
# FastAPI binds a `Depends(...)` target at import time, so depending on the
# factories directly would make those patches no-ops. Do not inline the wrappers.
def get_job_search_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheService, Depends(get_cache_service)],
) -> JobSearchService:
    """Get job search service instance."""
    return JobSearchService(db, cache)


def _get_cache_service_dependency() -> CacheService:
    return get_cache_service()


async def _get_saved_job_ids(db: AsyncSession, user: User | None, saved_only: bool) -> list[UUID] | None:
    if not saved_only:
        return None
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication is required for saved jobs",
        )
    saved_ids_result = await db.execute(
        select(SavedJob.job_id).where(SavedJob.user_id == user.id).order_by(SavedJob.created_at.desc())
    )
    return list(saved_ids_result.scalars().all())


def _get_job_search_service_dependency(
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheService, Depends(_get_cache_service_dependency)],
) -> JobSearchService:
    return get_job_search_service(db, cache)


@router.get(
    "/jobs",
    responses={
        401: {"description": "Authentication required for saved jobs"},
    },
)
@limiter.limit(RATE_LIMITS["jobs_list"])
async def list_jobs(
    request: Request,
    service: Annotated[JobSearchService, Depends(_get_job_search_service_dependency)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    filters: Annotated[JobListQuery, Query()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobListResponse:
    """List jobs with optional filters and search."""
    # The public listing never varies by user. Resolve (and validate) the
    # session only for the one user-scoped filter, saving an auth join on every
    # anonymous and signed-in homepage render.
    user = await get_optional_user(credentials, db) if filters.saved_only else None
    saved_job_ids = await _get_saved_job_ids(db, user, filters.saved_only)
    if filters.saved_only and not saved_job_ids:
        return JobListResponse(items=[], total=0, page=filters.page, page_size=filters.page_size)

    params = JobSearchParams(
        page=filters.page,
        page_size=filters.page_size,
        search=filters.search,
        company=filters.company,
        location=filters.location,
        category=filters.category,
        job_type=filters.job_type,
        work_mode=filters.work_mode,
        posted_within=filters.posted_within,
        match_ids=filters.match_ids,
        saved_only=filters.saved_only,
        saved_job_ids=saved_job_ids,
        active_only=True,
    )
    return await service.search(params)


@router.get("/jobs/filters/companies")
@limiter.limit(RATE_LIMITS["filters"])
async def get_companies(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheService, Depends(_get_cache_service_dependency)],
) -> list[str]:
    """Get all distinct company names (cached 15 min)."""
    cache_key = "filters:v2:companies"
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    repo = JobRepository(db)
    companies = await repo.get_distinct_companies()
    await cache.set(cache_key, companies, ttl=900)
    return companies


@router.get("/jobs/filters/locations", responses={401: {"description": "Authentication required for saved jobs"}})
@limiter.limit(RATE_LIMITS["filters"])
async def get_locations(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheService, Depends(_get_cache_service_dependency)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    search: Annotated[str | None, Query()] = None,
    company: Annotated[str | None, Query()] = None,
    location: Annotated[str | None, Query()] = None,
    category: Annotated[str | None, Query()] = None,
    job_type: Annotated[str | None, Query()] = None,
    work_mode: Annotated[str | None, Query()] = None,
    posted_within: Annotated[str | None, Query()] = None,
    match_ids: Annotated[str | None, Query()] = None,
    saved_only: Annotated[bool, Query()] = False,
) -> list[dict]:
    """Get location hierarchy with dynamic counts based on active non-location filters.

    Facet behavior: location counts ignore current location selection while applying
    all other active filters.
    """
    user = await get_optional_user(credentials, db) if saved_only else None
    saved_job_ids = await _get_saved_job_ids(db, user, saved_only)
    if saved_only and not saved_job_ids:
        return []

    params = JobSearchParams(
        page=1,
        page_size=20,
        search=search,
        company=company,
        location=location,
        category=category,
        job_type=job_type,
        work_mode=work_mode,
        posted_within=posted_within,
        match_ids=match_ids,
        saved_only=saved_only,
        saved_job_ids=saved_job_ids,
        active_only=True,
    )

    facet_cache_payload = {
        "search": params.search or "",
        "company": params.company or "",
        "category": params.category or "",
        "job_type": params.job_type or "",
        "work_mode": params.work_mode or "",
        "posted_within": params.posted_within or "",
        "match_ids": params.match_ids or "",
        "saved_only": params.saved_only,
        "user_id": str(user.id) if (saved_only and user) else "",
    }
    cache_key = (
        "filters:v2:locations_hierarchy:"
        + hashlib.sha256(json.dumps(facet_cache_payload, sort_keys=True).encode()).hexdigest()
    )
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    search_service = JobSearchService(db, cache=None)
    filtered_stmt, _ = search_service.build_filtered_stmt(params, include_location=False)

    location_service = LocationService(db)
    locations = await location_service.get_location_hierarchy_from_filtered_jobs(filtered_stmt)

    await cache.set(cache_key, locations, ttl=900)
    return locations


@router.get("/jobs/filters/categories")
@limiter.limit(RATE_LIMITS["filters"])
async def get_categories(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheService, Depends(_get_cache_service_dependency)],
) -> list[str]:
    """Get all distinct job categories (cached 15 min)."""
    cache_key = "filters:v2:categories"
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    repo = JobRepository(db)
    categories = await repo.get_distinct_categories()
    await cache.set(cache_key, categories, ttl=900)
    return categories


# Must stay above /jobs/{job_id}: FastAPI matches in declaration order, and the
# dynamic route would otherwise swallow this path and 422 on the UUID parse.
@router.get("/jobs/sitemap-ids")
@limiter.limit(RATE_LIMITS["sitemap"])
async def list_sitemap_job_ids(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=0, le=50000)] = 50000,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SitemapJobListResponse:
    """List job ids for sitemap generation.

    Scoped to the same rows the public listing serves, so the sitemap never
    advertises a page the site itself links from nowhere.

    Returns ``total`` alongside the slice so the caller can size its chunk set
    without a second request; pass ``limit=0`` to ask for the count only.
    """
    repo = JobRepository(db)
    total = await repo.count_sitemap_jobs()
    rows = await repo.get_sitemap_ids(limit=limit, offset=offset) if limit else []
    return SitemapJobListResponse(
        items=[SitemapJobResponse(id=job_id, posted_at=posted_at) for job_id, posted_at in rows],
        total=total,
    )


@router.get("/jobs/{job_id}", responses={404: {"description": "Not found"}, 410: {"description": "Job deactivated"}})
@limiter.limit(RATE_LIMITS["jobs_detail"])
async def get_job(
    request: Request,
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheService, Depends(_get_cache_service_dependency)],
) -> JobResponse:
    """Get a single job by ID (cached 5 min)."""
    record("job_detail_requests")
    # Try cache first
    cache_key = f"job:v2:{job_id}"
    cached = await cache.get(cache_key)
    if cached is not None:
        record("job_detail_response_cache_hits")
        return JobResponse(**cached)

    # Cache miss - fetch from DB
    record("job_detail_response_cache_misses")
    record("job_detail_db_reads")
    repo = JobRepository(db)
    job = await repo.get_detail_by_id(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=_JOB_NOT_FOUND)
    if job.is_active is not True:
        # Known-but-deactivated jobs are "gone", not "never existed": 410 tells
        # crawlers to drop the URL faster than a plain 404 would. Malformed or
        # unknown ids above keep the plain 404.
        raise HTTPException(status_code=410, detail=_JOB_NOT_FOUND)

    description_html, description_truncated = await sanitize_description_cached(job.description_text, cache)
    if description_truncated:
        logger.warning(
            "Truncated oversized job description",
            extra={"job_id": str(job.id), "description_bytes": len(job.description_text.encode("utf-8"))},
        )
    response = job_to_response(
        job,
        description_html=description_html,
        description_truncated=description_truncated,
    )

    # Cache the response (as dict for JSON serialization)
    await cache.set(cache_key, response.model_dump(), ttl=300)

    return response


@router.get("/jobs/{job_id}/related", responses={404: {"description": "Not found"}})
@limiter.limit(RATE_LIMITS["filters"])
async def get_related_jobs(
    request: Request,
    job_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheService, Depends(_get_cache_service_dependency)],
) -> JobListResponse:
    """List jobs related to one job (same company or category, cached 15 min)."""
    repo = JobRepository(db)
    job = await repo.get_detail_by_id(job_id)
    if not job or job.is_active is not True:
        # Mirror the detail route: deactivated jobs are gone, unknown ids not found.
        raise HTTPException(status_code=410 if job else 404, detail=_JOB_NOT_FOUND)

    service = RelatedJobsService(db, cache)
    return await service.related(
        job_id=job.id,
        company=job.company,
        category=enum_to_str(job.job_category),
    )


@router.get("/internal/bench/job-detail-counters", include_in_schema=False)
async def get_job_detail_benchmark_counters(request: Request) -> dict[str, int]:
    """Return opt-in benchmark counters from localhost with bearer auth only."""
    settings = get_settings()
    client_host = request.client.host if request.client else ""
    authorized = hmac.compare_digest(
        request.headers.get("authorization", ""),
        f"Bearer {settings.benchmark_counters_secret}",
    )
    if (
        not settings.benchmark_counters_enabled
        or not settings.benchmark_counters_secret
        or client_host not in {"127.0.0.1", "::1"}
        or not authorized
    ):
        raise HTTPException(status_code=404, detail="Not found")
    return snapshot()


@router.post("/jobs/{job_id}/click", responses={404: {"description": "Not found"}})
@limiter.limit(RATE_LIMITS["job_click"])
async def track_job_click(
    request: Request,
    job_id: UUID,
    db: DbSessionDependency,
    user: OptionalUserDependency,
    body: ClickRequest | None = None,
) -> ClickResponse:
    """Track a job click and return the apply URL with UTM params.

    Works for both authenticated and anonymous users.
    """
    # Get job by ID
    repo = JobRepository(db)
    job = await repo.get_by_id(job_id)

    if not job or job.is_active is not True:
        raise HTTPException(status_code=404, detail=_JOB_NOT_FOUND)

    # Hash the client IP for privacy
    client_ip = get_real_client_ip(request)
    ip_hash = _hash_client_ip(client_ip)

    # Get headers
    user_agent = request.headers.get("user-agent")
    referer = request.headers.get("referer")

    # Get UTM params from body
    utm_medium = body.utm_medium if body else None
    utm_campaign = body.utm_campaign if body else None

    # Create JobClick record
    click = JobClick(
        job_id=job_id,
        user_id=user.id if user else None,
        clicked_at=datetime.now(timezone.utc),
        utm_source="internnexus",
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        ip_hash=ip_hash,
        user_agent=user_agent[:500] if user_agent else None,
        referer=referer[:500] if referer else None,
    )
    db.add(click)

    await commit_or_500(db, operation="track job click")

    # Add UTM params to apply URL
    apply_url = add_utm_params(
        job.apply_url,
        source="internnexus",
        medium=utm_medium,
        campaign=utm_campaign,
    )

    return ClickResponse(apply_url=apply_url, job_id=str(job_id))
