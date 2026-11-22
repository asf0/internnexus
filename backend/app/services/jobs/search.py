"""Job search service with caching and full-text search."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import any_, bindparam, false, func, or_, select
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only
from sqlalchemy.sql import Select

from app.schemas.mappers import job_to_summary
from app.schemas.jobs import JobListResponse
from app.infra.cache.cache_service import CacheService
from app.models import Job
from app.services.jobs.posted_within import DEFAULT_JOB_POSTED_WITHIN_DAYS, posted_within_cutoff
from app.services.jobs.query_parser import ParsedSearch, SearchTerm, parse_search_query, split_pipe_values

MAX_SEARCH_LENGTH = 100
MAX_PAGINATION_OFFSET = 100_000
JobSelect = Select[Job]


@dataclass
class JobSearchParams:
    """Parameters for job search."""

    page: int = 1
    page_size: int = 20
    search: str | None = None
    company: str | None = None
    location: str | None = None
    category: str | None = None
    job_type: str | None = None
    work_mode: str | None = None
    posted_within: str | None = None
    match_ids: str | None = None
    saved_only: bool = False
    saved_job_ids: list[UUID] | None = None
    active_only: bool = False
    match_mode: str = "all"

    def __post_init__(self) -> None:
        self.page = max(1, self.page)
        self.page_size = min(max(1, self.page_size), 100)
        self.page = min(self.page, (MAX_PAGINATION_OFFSET // self.page_size) + 1)
        self.search = self.search[:MAX_SEARCH_LENGTH].strip() if self.search else None
        self.match_mode = self.match_mode if self.match_mode in {"all", "any"} else "all"


class JobSearchService:
    """Service for job search with full-text search."""

    def __init__(self, session: AsyncSession, cache: CacheService | None = None):
        self.session = session
        self.cache = cache

    def _filter_cache_parts(self, params: JobSearchParams) -> list[str]:
        """Return the filter-only key parts shared by lists and counts.

        Page and page size are deliberately excluded: the filtered count is
        identical for every page of the same result set. Keeping it out of the
        count key lets pages 2..N reuse the count computed for page 1.
        """
        return [
            f"search:{params.search or ''}",
            f"company:{params.company or ''}",
            f"location:{params.location or ''}",
            f"category:{params.category or ''}",
            f"type:{params.job_type or ''}",
            f"mode:{params.work_mode or ''}",
            f"posted:{params.posted_within or ''}",
            f"match:{params.match_ids or ''}",
            f"saved:{'1' if params.saved_only else '0'}",
            f"active:{'1' if params.active_only else '0'}",
            f"match_mode:{params.match_mode}",
            "saved_ids:"
            + (
                hashlib.sha256("|".join(str(job_id) for job_id in (params.saved_job_ids or [])).encode()).hexdigest()
                if params.saved_job_ids
                else ""
            ),
        ]

    def _cache_key(self, params: JobSearchParams) -> str:
        """Generate the response cache key (page-specific)."""
        key_parts = [
            f"page:{params.page}",
            f"size:{params.page_size}",
            *self._filter_cache_parts(params),
        ]
        return "jobs:v2:" + hashlib.sha256("|".join(key_parts).encode()).hexdigest()

    def _count_cache_key(self, params: JobSearchParams) -> str:
        """Generate the count cache key (shared across pages)."""
        return "jobs:count:v1:" + hashlib.sha256(
            "|".join(self._filter_cache_parts(params)).encode()
        ).hexdigest()

    async def search(self, params: JobSearchParams) -> JobListResponse:
        """Execute job search with given parameters."""
        cache_key = self._cache_key(params)

        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return JobListResponse(**cached)

        result = await self._execute_search(params)

        if self.cache:
            await self.cache.set(cache_key, result.model_dump(), ttl=300)

        return result

    async def _execute_search(self, params: JobSearchParams) -> JobListResponse:
        """Execute the actual search query."""
        stmt, valid_ids = self.build_filtered_stmt(params)
        stmt = self._apply_ordering(stmt, valid_ids)

        total = await self._get_total_count(stmt, params)
        summary_stmt = stmt.options(
            load_only(
                Job.id,
                Job.source,
                Job.title,
                Job.company,
                Job.location,
                Job.city,
                Job.state,
                Job.country,
                Job.apply_url,
                Job.job_category,
                Job.job_type,
                Job.work_mode,
                Job.posted_at,
                Job.is_active,
            )
        )
        items = await self._paginate(summary_stmt, params.page, params.page_size)

        return JobListResponse(
            items=[job_to_summary(job) for job in items],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    def build_filtered_stmt(
        self, params: JobSearchParams, include_location: bool = True
    ) -> tuple[JobSelect, list[UUID]]:
        """Build the filtered base statement used by list and facet endpoints.

        Args:
            params: Search parameters
            include_location: Whether to apply the location filter (False for location facets)
        """
        base_stmt: JobSelect = select(Job)

        valid_ids = self._parse_match_ids(params.match_ids)
        saved_job_ids = params.saved_job_ids or []

        if params.saved_only:
            if not saved_job_ids:
                return base_stmt.where(false()), []
            if valid_ids:
                saved_set = set(saved_job_ids)
                valid_ids = [job_id for job_id in valid_ids if job_id in saved_set]
                if not valid_ids:
                    return base_stmt.where(false()), []
            else:
                valid_ids = saved_job_ids

        search_ordering: tuple[Any, ...] = ()
        if params.search:
            parsed = parse_search_query(params.search)
            base_stmt, search_ordering = self._apply_keyword_search(
                base_stmt,
                params.search,
                parsed,
                params.match_mode,
            )

        stmt = self._apply_filters(
            base_stmt,
            params,
            valid_ids,
            include_location=include_location,
        )
        if search_ordering and not valid_ids:
            stmt = stmt.order_by(*search_ordering)
        return stmt, valid_ids

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

    def _apply_keyword_search(
        self,
        stmt: JobSelect,
        search: str,
        parsed: ParsedSearch,
        match_mode: str = "all",
    ) -> tuple[JobSelect, tuple[Any, ...]]:
        """Apply keyword search in SQL without materializing every matching ID."""
        tsquery = self._build_tsquery(search, parsed, match_mode)

        if tsquery:
            query = func.to_tsquery("english", tsquery)
            return (
                stmt.where(Job.search_vector.op("@@")(query)),
                (func.ts_rank_cd(Job.search_vector, query).desc(), Job.id.asc()),
            )

        search_term = f"%{search}%"
        return (
            stmt.where(
                or_(
                    Job.title.ilike(search_term),
                    Job.company.ilike(search_term),
                    Job.location.ilike(search_term),
                )
            ),
            (Job.id.asc(),),
        )

    def _build_tsquery(self, search: str, parsed: ParsedSearch, match_mode: str = "all") -> str:
        """Build PostgreSQL tsquery from search."""
        if parsed.is_boolean and parsed.expression:
            return self._build_expr_tsquery(parsed.expression)
        return self._build_fulltext_query(search, match_mode)

    def _build_fulltext_query(self, search: str, match_mode: str = "all") -> str:
        """Convert search terms to PostgreSQL tsquery format."""
        terms = re.findall(r"\w+", search.lower())
        if not terms:
            return ""
        operator = " | " if match_mode == "any" else " & "
        return operator.join(f"{term}:*" for term in terms[:10])

    def _build_term_tsquery(self, term: SearchTerm) -> str:
        value = term.value.lower().strip()
        value = re.sub(r"[&|!():*<>\"]", " ", value)
        words = [w for w in re.findall(r"\w+", value) if w][:5]
        if not words:
            return ""
        if term.is_exact:
            return "(" + " <-> ".join(words) + ")"
        return " & ".join(f"{w}:*" for w in words)

    def _build_expr_tsquery(self, expr: Any) -> str:
        if isinstance(expr, SearchTerm):
            return self._build_term_tsquery(expr)

        parts = [self._build_expr_tsquery(term) for term in expr.terms if term]
        parts = [part for part in parts if part]
        if not parts:
            return ""

        operator_map = {
            "NOT": lambda tokens: f"!({tokens[0]})",
            "AND": lambda tokens: "(" + " & ".join(tokens) + ")",
            "OR": lambda tokens: "(" + " | ".join(tokens) + ")",
        }
        formatter = operator_map.get(expr.operator)
        if formatter is None:
            return ""
        return formatter(parts)

    def _apply_filters(
        self,
        stmt: JobSelect,
        params: JobSearchParams,
        valid_ids: list[UUID],
        include_location: bool = True,
    ) -> JobSelect:
        """Apply filters to the query."""
        if params.active_only:
            stmt = stmt.where(Job.is_active.is_(True))
        if valid_ids:
            stmt = stmt.where(Job.id == any_(self._uuid_array_parameter("filter_job_ids", valid_ids)))

        if params.company:
            companies = split_pipe_values(params.company, drop_empty=False)
            stmt = stmt.where(Job.company.in_(companies))

        if include_location and params.location:
            stmt = self._apply_location_filter(stmt, params.location)

        if params.category:
            categories = split_pipe_values(params.category, drop_empty=False)
            stmt = stmt.where(Job.job_category.in_(categories))

        if params.job_type:
            stmt = self._apply_job_type_filter(stmt, params.job_type)

        if params.work_mode:
            stmt = self._apply_work_mode_filter(stmt, params.work_mode)

        if params.posted_within:
            cutoff = posted_within_cutoff(params.posted_within, datetime.now(timezone.utc))
            if cutoff is not None:
                stmt = stmt.where(Job.posted_at >= cutoff)
        elif not params.saved_only:
            cutoff = datetime.now(timezone.utc) - timedelta(days=DEFAULT_JOB_POSTED_WITHIN_DAYS)
            stmt = stmt.where(Job.posted_at >= cutoff)

        return stmt

    def _apply_location_filter(self, stmt: JobSelect, location: str) -> JobSelect:
        """Apply location filter."""
        locations = split_pipe_values(location, drop_empty=True)
        if not locations:
            return stmt

        conditions = []
        for loc in locations:
            conditions.append(
                or_(
                    Job.location.ilike(f"%{loc}%"),
                    Job.city.ilike(f"%{loc}%"),
                    Job.state.ilike(f"%{loc}%"),
                    Job.country == loc,
                )
            )

        return stmt.where(or_(*conditions)) if conditions else stmt

    def _apply_job_type_filter(self, stmt: JobSelect, job_type: str) -> JobSelect:
        """Apply job type filter."""
        job_types = split_pipe_values(job_type, drop_empty=False)
        conditions = []
        for jt in job_types:
            if jt == "internship":
                conditions.append(or_(Job.job_type == "internship", Job.title.ilike("%intern%")))
            elif jt == "full-time":
                conditions.append(or_(Job.job_type == "full_time", Job.title.ilike("%full%time%")))
            elif jt == "part-time":
                conditions.append(or_(Job.job_type == "part_time", Job.title.ilike("%part%time%")))
        return stmt.where(or_(*conditions)) if conditions else stmt

    def _apply_work_mode_filter(self, stmt: JobSelect, work_mode: str) -> JobSelect:
        """Apply work mode filter."""
        modes = split_pipe_values(work_mode, drop_empty=False)
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

    def _apply_ordering(
        self,
        stmt: JobSelect,
        valid_ids: list[UUID],
    ) -> JobSelect:
        """Apply ordering to the query."""
        if valid_ids and len(valid_ids) > 0:
            stmt = stmt.order_by(
                func.array_position(
                    self._uuid_array_parameter("filter_job_ids", valid_ids),
                    Job.id,
                )
            )
        return stmt

    @staticmethod
    def _uuid_array_parameter(name: str, values: list[UUID]):
        """Bind an arbitrary UUID list as one PostgreSQL array parameter."""
        return bindparam(
            name,
            value=values,
            type_=ARRAY(PG_UUID(as_uuid=True)),
        )

    async def _get_total_count(self, stmt: JobSelect, params: JobSearchParams) -> int:
        """Return the filtered count, sharing it across pages when cached."""
        if self.cache is None:
            return await self._count_results(stmt)

        count_key = self._count_cache_key(params)
        cached_total = await self.cache.get(count_key)
        if cached_total is not None:
            return int(cached_total)

        total = await self._count_results(stmt)
        await self.cache.set(count_key, total, ttl=300)
        return total

    async def _count_results(self, stmt: JobSelect) -> int:
        """Count total results.

        Swaps the column list for `count(*)` rather than wrapping the statement
        in a subquery. Wrapping made the subquery select every `Job` column --
        including the TOASTed `description_text` -- purely to count rows, which
        measured 24.5M block reads and 2.1B buffer hits across 10,411 calls.
        `maintain_column_froms=True` preserves the FROM that the original
        columns clause implied, so the filters still apply unchanged.

        Plain `count(*)` is correct because the builder never joins: every
        filter in `_apply_filters` is on `jobs` itself. Revisit if a join is
        ever introduced -- a one-to-many join would need `count(DISTINCT id)`.
        """
        count_stmt = (
            stmt.order_by(None)
            .with_only_columns(func.count(), maintain_column_froms=True)
        )
        result = await self.session.execute(count_stmt)
        return result.scalar() or 0

    async def _paginate(self, stmt: JobSelect, page: int, page_size: int) -> list[Job]:
        """Paginate results."""
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
