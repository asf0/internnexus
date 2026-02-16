"""Job search service with caching and vector search."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import JobListResponse, JobResponse
from app.cache.redis_pool import RedisService
from app.models import Job
from app.repositories.job import JobRepository
from app.services.embedding_service import EmbeddingService
from app.services.search_parser import ParsedSearch, parse_search_query

VECTOR_SEARCH_THRESHOLD = 0.55
VECTOR_MATCH_THRESHOLD = 0.45
VECTOR_LIMIT = 100
KEYWORD_BOOST = 0.1
MAX_SEARCH_LENGTH = 100


class JobSearchParams:
    """Parameters for job search."""

    def __init__(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        company: str | None = None,
        location: str | None = None,
        category: str | None = None,
        visa_sponsored: bool | None = None,
        f1_friendly: bool | None = None,
        job_type: str | None = None,
        work_mode: str | None = None,
        posted_within: str | None = None,
        match_ids: str | None = None,
    ):
        self.page = max(1, page)
        self.page_size = min(max(1, page_size), 100)
        self.search = search[:MAX_SEARCH_LENGTH].strip() if search else None
        self.company = company
        self.location = location
        self.category = category
        self.visa_sponsored = visa_sponsored
        self.f1_friendly = f1_friendly
        self.job_type = job_type
        self.work_mode = work_mode
        self.posted_within = posted_within
        self.match_ids = match_ids


class JobSearchService:
    """Service for job search with vector and keyword search."""

    def __init__(self, session: AsyncSession, cache: RedisService | None = None):
        self.session = session
        self.job_repo = JobRepository(session)
        self.cache = cache

    async def search(self, params: JobSearchParams) -> JobListResponse:
        """Execute job search with given parameters."""
        base_stmt = select(Job).where(Job.is_active == True)  # noqa: E712

        valid_ids = self._parse_match_ids(params.match_ids)
        preserve_order = len(valid_ids) > 0

        result_order: list[UUID] = []

        if params.search:
            parsed = parse_search_query(params.search)
            keyword_ids, vector_results = await self._execute_search(
                params.search, parsed, base_stmt, valid_ids
            )
            result_order = self._merge_results(keyword_ids, vector_results, valid_ids)

        stmt = self._apply_filters(base_stmt, params, valid_ids, result_order)
        stmt = self._apply_ordering(stmt, params, valid_ids, result_order)

        total = await self._count_results(stmt)
        items = await self._paginate(stmt, params.page, params.page_size)

        return JobListResponse(
            items=[JobResponse.model_validate(job) for job in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    def _parse_match_ids(self, match_ids: str | None) -> list[UUID]:
        """Parse match_ids parameter into list of UUIDs."""
        if not match_ids:
            return []
        valid_ids = []
        for raw_id in match_ids.split("|"):
            raw_id = raw_id.strip()
            if raw_id:
                try:
                    valid_ids.append(UUID(raw_id))
                except ValueError:
                    continue
        return valid_ids

    async def _execute_search(
        self,
        search: str,
        parsed: ParsedSearch,
        base_stmt,
        valid_ids: list[UUID],
    ) -> tuple[set[UUID], list[tuple[UUID, float]]]:
        """Execute keyword and vector search."""
        keyword_ids = await self._keyword_search(search, parsed, base_stmt)
        vector_results: list[tuple[UUID, float]] = []

        if not parsed.is_boolean:
            threshold = VECTOR_MATCH_THRESHOLD if valid_ids else VECTOR_SEARCH_THRESHOLD
            vector_results = await self._vector_search(search, threshold)

        return keyword_ids, vector_results

    async def _keyword_search(self, search: str, parsed: ParsedSearch, base_stmt) -> set[UUID]:
        """Execute full-text keyword search."""
        tsquery = self._build_tsquery(search, parsed)

        if tsquery:
            stmt = base_stmt.where(Job.search_vector.op("@@")(func.to_tsquery("english", tsquery)))
            result = await self.session.execute(stmt)
            return {row.id for row in result.scalars().all()}

        search_term = f"%{search}%"
        stmt = base_stmt.where(
            or_(
                Job.title.ilike(search_term),
                Job.company.ilike(search_term),
                Job.location.ilike(search_term),
            )
        )
        result = await self.session.execute(stmt)
        return {row.id for row in result.scalars().all()}

    def _build_tsquery(self, search: str, parsed: ParsedSearch) -> str:
        """Build PostgreSQL tsquery from search."""
        if parsed.is_boolean and parsed.expression:
            return self._build_boolean_tsquery(parsed.expression)
        return self._build_fulltext_query(search)

    def _build_fulltext_query(self, search: str) -> str:
        """Convert search terms to PostgreSQL tsquery format."""
        terms = re.findall(r"\w+", search.lower())
        if not terms:
            return ""
        return " & ".join(f"{term}:*" for term in terms[:10])

    def _build_boolean_tsquery(self, expr) -> str:
        """Convert boolean expression to PostgreSQL tsquery format."""
        from app.services.search_parser import BooleanExpr, SearchTerm

        def build_term(term: SearchTerm) -> str:
            value = term.value.lower().strip()
            value = re.sub(r"[&|!():*<>\"]", " ", value)
            words = [w for w in re.findall(r"\w+", value) if w][:5]
            if not words:
                return ""
            if term.is_exact:
                return "(" + " <-> ".join(words) + ")"
            return " & ".join(f"{w}:*" for w in words)

        def build_expr(e) -> str:
            if isinstance(e, SearchTerm):
                return build_term(e)

            parts = [build_expr(t) for t in e.terms if t]
            parts = [p for p in parts if p]
            if not parts:
                return ""

            if e.operator == "NOT":
                return f"!({parts[0]})" if parts else ""
            if e.operator == "AND":
                return "(" + " & ".join(parts) + ")"
            if e.operator == "OR":
                return "(" + " | ".join(parts) + ")"
            return ""

        return build_expr(expr)

    async def _vector_search(self, search: str, threshold: float) -> list[tuple[UUID, float]]:
        """Execute vector similarity search."""
        embedding = await self._get_embedding(search)
        if embedding is None:
            return []

        stmt = (
            select(
                Job.id,
                (1 - Job.description_embedding.cosine_distance(embedding)).label("similarity"),
            )
            .where(Job.is_active == True)  # noqa: E712
            .where(Job.description_embedding.isnot(None))
            .where((1 - Job.description_embedding.cosine_distance(embedding)) >= threshold)
            .order_by((1 - Job.description_embedding.cosine_distance(embedding)).desc())
            .limit(VECTOR_LIMIT)
        )

        result = await self.session.execute(stmt)
        return [(row.id, float(row.similarity)) for row in result.all()]

    async def _get_embedding(self, text: str) -> list[float] | None:
        """Get embedding from cache or generate."""
        if self.cache:
            cached = await self.cache.get_embedding(text)
            if cached:
                return cached

        try:
            embedder = EmbeddingService()
            embedding = await embedder.embed(text)
            if self.cache:
                await self.cache.set_embedding(text, embedding)
            return embedding
        except RuntimeError:
            return None

    def _merge_results(
        self,
        keyword_ids: set[UUID],
        vector_results: list[tuple[UUID, float]],
        valid_ids: list[UUID],
    ) -> list[UUID]:
        """Merge keyword and vector search results."""
        vector_ids = {vid for vid, _ in vector_results}
        all_ids = keyword_ids | vector_ids

        if not all_ids:
            return list(keyword_ids)

        vector_scores = {vid: score for vid, score in vector_results}

        def sort_key(job_id: UUID) -> tuple:
            in_keyword = job_id in keyword_ids
            vector_score = vector_scores.get(job_id, 0.0)
            boost = KEYWORD_BOOST if in_keyword else 0.0
            return (-(vector_score + boost),)

        return sorted(all_ids, key=sort_key)

    def _apply_filters(
        self, stmt, params: JobSearchParams, valid_ids: list[UUID], result_order: list[UUID]
    ):
        """Apply filters to the query."""
        if valid_ids:
            stmt = stmt.where(Job.id.in_(valid_ids))
        elif result_order:
            stmt = stmt.where(Job.id.in_(result_order))

        if params.company:
            companies = [c.strip() for c in params.company.split("|")]
            stmt = stmt.where(Job.company.in_(companies))

        if params.location:
            locations = [loc.strip() for loc in params.location.split("|") if loc.strip()]
            if locations:
                stmt = stmt.where(or_(*[Job.location.ilike(f"%{loc}%") for loc in locations]))

        if params.category:
            categories = [c.strip() for c in params.category.split("|")]
            stmt = stmt.where(Job.job_category.in_(categories))

        if params.visa_sponsored is not None:
            stmt = stmt.where(Job.visa_sponsored == params.visa_sponsored)

        if params.f1_friendly is not None:
            stmt = stmt.where(Job.f1_friendly == params.f1_friendly)

        if params.job_type:
            stmt = self._apply_job_type_filter(stmt, params.job_type)

        if params.work_mode:
            stmt = self._apply_work_mode_filter(stmt, params.work_mode)

        if params.posted_within:
            stmt = self._apply_posted_within_filter(stmt, params.posted_within)

        return stmt

    def _apply_job_type_filter(self, stmt, job_type: str):
        """Apply job type filter."""
        job_types = [jt.strip() for jt in job_type.split("|")]
        conditions = []
        for jt in job_types:
            if jt == "internship":
                conditions.append(or_(Job.job_type == "internship", Job.title.ilike("%intern%")))
            elif jt == "full-time":
                conditions.append(or_(Job.job_type == "full_time", Job.title.ilike("%full%time%")))
            elif jt == "part-time":
                conditions.append(or_(Job.job_type == "part_time", Job.title.ilike("%part%time%")))
        return stmt.where(or_(*conditions)) if conditions else stmt

    def _apply_work_mode_filter(self, stmt, work_mode: str):
        """Apply work mode filter."""
        modes = [wm.strip() for wm in work_mode.split("|")]
        conditions = []
        for wm in modes:
            if wm == "remote":
                conditions.append(
                    or_(
                        Job.work_mode == "remote",
                        Job.title.ilike("%remote%"),
                        Job.location.ilike("%remote%"),
                    )
                )
            elif wm == "hybrid":
                conditions.append(
                    or_(
                        Job.work_mode == "hybrid",
                        Job.title.ilike("%hybrid%"),
                        Job.location.ilike("%hybrid%"),
                    )
                )
            elif wm == "on-site":
                conditions.append(
                    or_(
                        Job.work_mode == "on_site",
                        Job.title.ilike("%on-site%"),
                        Job.location.ilike("%in-office%"),
                    )
                )
        return stmt.where(or_(*conditions)) if conditions else stmt

    def _apply_posted_within_filter(self, stmt, posted_within: str):
        """Apply posted within filter."""
        now = datetime.now(timezone.utc)
        cutoff = None
        if posted_within == "24h":
            cutoff = now - timedelta(hours=24)
        elif posted_within == "week":
            cutoff = now - timedelta(days=7)
        elif posted_within == "month":
            cutoff = now - timedelta(days=30)
        return stmt.where(Job.posted_at >= cutoff) if cutoff else stmt

    def _apply_ordering(
        self, stmt, params: JobSearchParams, valid_ids: list[UUID], result_order: list[UUID]
    ):
        """Apply ordering to the query."""
        if valid_ids and len(valid_ids) > 0:
            ordering = case(
                {uid: idx for idx, uid in enumerate(valid_ids)},
                value=Job.id,
                else_=len(valid_ids),
            )
            stmt = stmt.order_by(ordering)
        elif result_order:
            ordering = case(
                {uid: idx for idx, uid in enumerate(result_order)},
                value=Job.id,
                else_=len(result_order),
            )
            stmt = stmt.order_by(ordering)
        return stmt

    async def _count_results(self, stmt) -> int:
        """Count total results."""
        count_stmt = select(func.count()).select_from(stmt.subquery())
        result = await self.session.execute(count_stmt)
        return result.scalar() or 0

    async def _paginate(self, stmt, page: int, page_size: int) -> list[Job]:
        """Paginate results."""
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
