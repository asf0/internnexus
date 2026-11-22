"""Related-jobs service backing the public job detail page's link modules."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.cache.cache_service import CacheService
from app.repositories.job import JobRepository
from app.schemas.jobs import JobListResponse, JobSummaryResponse

RELATED_JOBS_LIMIT = 10
RELATED_CACHE_TTL_SECONDS = 900
_RELATED_CACHE_PREFIX = "related:v1:"


class RelatedJobsService:
    """Resolve a small, cached slice of jobs related to one job."""

    def __init__(self, session: AsyncSession, cache: CacheService | None = None):
        self.session = session
        self.cache = cache

    async def related(self, job_id: UUID, company: str, category: str | None) -> JobListResponse:
        """Same-company jobs first, then same-category, capped and cached."""
        cache_key = f"{_RELATED_CACHE_PREFIX}{job_id}"
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return JobListResponse(**cached)

        repo = JobRepository(self.session)
        rows = await repo.get_related_candidates(
            job_id=job_id,
            company=company,
            category=category,
            limit=RELATED_JOBS_LIMIT,
        )
        items = [JobSummaryResponse.model_validate(job) for job in rows]
        response = JobListResponse(items=items, total=len(items), page=1, page_size=RELATED_JOBS_LIMIT)

        if self.cache:
            await self.cache.set(cache_key, response.model_dump(), ttl=RELATED_CACHE_TTL_SECONDS)
        return response
