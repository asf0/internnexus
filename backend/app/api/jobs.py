"""Jobs API endpoints - refactored to use service layer."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import JobListResponse, JobResponse
from app.cache.redis_pool import RedisService, get_redis_service
from app.db import get_db
from app.rate_limiter import RATE_LIMITS, limiter
from app.repositories.job import JobRepository
from app.services.job_search import JobSearchParams, JobSearchService

router = APIRouter()


async def get_job_search_service(
    db: AsyncSession = Depends(get_db),
    cache: RedisService = Depends(get_redis_service),
) -> JobSearchService:
    """Get job search service instance."""
    return JobSearchService(db, cache)


@router.get("/jobs", response_model=JobListResponse)
@limiter.limit(RATE_LIMITS["jobs_list"])
async def list_jobs(
    request: Request,
    service: JobSearchService = Depends(get_job_search_service),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    company: str | None = Query(None),
    location: str | None = Query(None),
    category: str | None = Query(None),
    visa_sponsored: bool | None = Query(None),
    f1_friendly: bool | None = Query(None),
    job_type: str | None = Query(None),
    work_mode: str | None = Query(None),
    posted_within: str | None = Query(None),
    match_ids: str | None = Query(None),
) -> JobListResponse:
    """List jobs with optional filters and search."""
    params = JobSearchParams(
        page=page,
        page_size=page_size,
        search=search,
        company=company,
        location=location,
        category=category,
        visa_sponsored=visa_sponsored,
        f1_friendly=f1_friendly,
        job_type=job_type,
        work_mode=work_mode,
        posted_within=posted_within,
        match_ids=match_ids,
    )
    return await service.search(params)


@router.get("/jobs/filters/companies")
@limiter.limit(RATE_LIMITS["filters"])
async def get_companies(
    request: Request,
    db: AsyncSession = Depends(get_db),
    cache: RedisService = Depends(get_redis_service),
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
    cache: RedisService = Depends(get_redis_service),
) -> list[str]:
    """Get all distinct locations (cached 5 min)."""
    cache_key = "filters:locations"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    repo = JobRepository(db)
    locations = await repo.get_distinct_locations()
    await cache.set(cache_key, locations, ttl=300)
    return locations


@router.get("/jobs/filters/categories")
@limiter.limit(RATE_LIMITS["filters"])
async def get_categories(
    request: Request,
    db: AsyncSession = Depends(get_db),
    cache: RedisService = Depends(get_redis_service),
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
    job_id: str,
    db: AsyncSession = Depends(get_db),
    cache: RedisService = Depends(get_redis_service),
) -> JobResponse:
    """Get a single job by ID (cached 5 min)."""
    from uuid import UUID

    try:
        uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    # Try cache first
    cache_key = f"job:{job_id}"
    cached = await cache.get(cache_key)
    if cached:
        return JobResponse(**cached)

    # Cache miss - fetch from DB
    repo = JobRepository(db)
    job = await repo.get_by_id(uuid)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.is_active is not True:
        raise HTTPException(status_code=404, detail="Job not found")

    response = JobResponse.model_validate(job)

    # Cache the response (as dict for JSON serialization)
    await cache.set(cache_key, response.model_dump(), ttl=300)

    return response
