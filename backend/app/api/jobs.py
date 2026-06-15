"""Jobs API endpoints - refactored to use service layer."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.mappers import job_to_response
from app.api.schemas import JobListResponse, JobResponse
from app.auth.dependencies import get_optional_user
from app.cache.cache_service import CacheService, get_cache_service
from app.db import get_db
from app.models import JobClick, SavedJob, User
from app.rate_limiter import RATE_LIMITS, limiter
from app.repositories.job import JobRepository
from app.services.job_search import JobSearchParams, JobSearchService
from app.services.location_service import LocationService
from app.utils import add_utm_params
from app.utils.db import commit_or_500

router = APIRouter()


class ClickRequest(BaseModel):
    """Request body for job click tracking."""

    utm_medium: str | None = None
    utm_campaign: str | None = None


class ClickResponse(BaseModel):
    """Response for job click tracking."""

    apply_url: str
    job_id: str


async def get_job_search_service(
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service),
) -> JobSearchService:
    """Get job search service instance."""
    return JobSearchService(db, cache)


async def _get_cache_service_dependency() -> CacheService:
    return await get_cache_service()




async def _get_saved_job_ids(db: AsyncSession, user: User | None, saved_only: bool) -> list[UUID] | None:
    if not saved_only:
        return None
    if not user:
        return []
    saved_ids_result = await db.execute(
        select(SavedJob.job_id)
        .where(SavedJob.user_id == user.id)
        .order_by(SavedJob.created_at.desc())
    )
    return list(saved_ids_result.scalars().all())


async def _get_job_search_service_dependency(
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(_get_cache_service_dependency),
) -> JobSearchService:
    return await get_job_search_service(db, cache)


@router.get("/jobs", response_model=JobListResponse)
@limiter.limit(RATE_LIMITS["jobs_list"])
async def list_jobs(
    request: Request,
    service: JobSearchService = Depends(_get_job_search_service_dependency),
    user: User | None = Depends(get_optional_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    company: str | None = Query(None),
    location: str | None = Query(None),
    category: str | None = Query(None),
    job_type: str | None = Query(None),
    work_mode: str | None = Query(None),
    posted_within: str | None = Query(None),
    match_ids: str | None = Query(None),
    saved_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """List jobs with optional filters and search."""
    saved_job_ids = await _get_saved_job_ids(db, user, saved_only)
    if saved_only and not saved_job_ids:
        return JobListResponse(items=[], total=0, page=page, page_size=page_size)

    params = JobSearchParams(
        page=page,
        page_size=page_size,
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
    )
    return await service.search(params)


@router.get("/jobs/filters/companies")
@limiter.limit(RATE_LIMITS["filters"])
async def get_companies(
    request: Request,
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(_get_cache_service_dependency),
) -> list[str]:
    """Get all distinct company names (cached 5 min)."""
    cache_key = "filters:companies"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    repo = JobRepository(db)
    companies = await repo.get_distinct_companies()
    await cache.set(cache_key, companies, ttl=300)
    return companies


@router.get("/jobs/filters/locations")
@limiter.limit(RATE_LIMITS["filters"])
async def get_locations(
    request: Request,
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(_get_cache_service_dependency),
    user: User | None = Depends(get_optional_user),
    search: str | None = Query(None),
    company: str | None = Query(None),
    location: str | None = Query(None),
    category: str | None = Query(None),
    job_type: str | None = Query(None),
    work_mode: str | None = Query(None),
    posted_within: str | None = Query(None),
    match_ids: str | None = Query(None),
    saved_only: bool = Query(False),
) -> list[dict]:
    """Get location hierarchy with dynamic counts based on active non-location filters.

    Facet behavior: location counts ignore current location selection while applying
    all other active filters.
    """
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
        "filters:locations_hierarchy:"
        + hashlib.md5(json.dumps(facet_cache_payload, sort_keys=True).encode()).hexdigest()
    )
    cached = await cache.get(cache_key)
    if cached:
        return cached

    search_service = JobSearchService(db, cache=None)
    filtered_stmt, _, _ = await search_service.build_filtered_stmt(params, include_location=False)

    location_service = LocationService(db)
    locations = await location_service.get_location_hierarchy_from_filtered_jobs(filtered_stmt)

    await cache.set(cache_key, locations, ttl=300)
    return locations


@router.get("/jobs/filters/categories")
@limiter.limit(RATE_LIMITS["filters"])
async def get_categories(
    request: Request,
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(_get_cache_service_dependency),
) -> list[str]:
    """Get all distinct job categories (cached 5 min)."""
    cache_key = "filters:categories"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    repo = JobRepository(db)
    categories = await repo.get_distinct_categories()
    await cache.set(cache_key, categories, ttl=300)
    return categories


@router.get("/jobs/{job_id}", response_model=JobResponse)
@limiter.limit(RATE_LIMITS["jobs_detail"])
async def get_job(
    request: Request,
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(_get_cache_service_dependency),
) -> JobResponse:
    """Get a single job by ID (cached 5 min)."""
    # Try cache first
    cache_key = f"job:{job_id}"
    cached = await cache.get(cache_key)
    if cached:
        return JobResponse(**cached)

    # Cache miss - fetch from DB
    repo = JobRepository(db)
    job = await repo.get_by_id(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.is_active is not True:
        raise HTTPException(status_code=404, detail="Job not found")

    response = job_to_response(job)

    # Cache the response (as dict for JSON serialization)
    await cache.set(cache_key, response.model_dump(), ttl=300)

    return response


@router.post("/jobs/{job_id}/click", response_model=ClickResponse)
@limiter.limit(RATE_LIMITS["job_click"])
async def track_job_click(
    request: Request,
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
    body: ClickRequest | None = None,
) -> ClickResponse:
    """Track a job click and return the apply URL with UTM params.

    Works for both authenticated and anonymous users.
    """
    # Get job by ID
    repo = JobRepository(db)
    job = await repo.get_by_id(job_id)

    if not job or job.is_active is not True:
        raise HTTPException(status_code=404, detail="Job not found")

    # Hash the client IP for privacy
    client_ip = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(f"click:{client_ip}".encode()).hexdigest()[:16]

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
