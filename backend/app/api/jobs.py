from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import and_, case, distinct, func, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import JobListResponse, JobResponse
from app.db import get_db
from app.models import Job
from app.rate_limiter import RATE_LIMITS, limiter
from app.services.embedding_service import EmbeddingService
from app.services.search_parser import (
    BooleanExpr,
    ParsedSearch,
    SearchTerm,
    parse_search_query,
)

router = APIRouter()
logger = logging.getLogger(__name__)

VECTOR_SEARCH_THRESHOLD = 0.55
VECTOR_LIMIT = 100
KEYWORD_BOOST = 0.1


def _get_redis():
    try:
        import redis.asyncio as redis
        from app.config import get_settings

        settings = get_settings()
        return redis.from_url(settings.redis_url, decode_responses=True)
    except Exception:
        return None


async def _get_cached_embedding(query: str) -> list[float] | None:
    r = _get_redis()
    if not r:
        return None
    try:
        cache_key = f"embed:{hashlib.md5(query.encode()).hexdigest()}"
        cached = await r.get(cache_key)
        if cached:
            await r.close()
            return json.loads(cached)
        await r.close()
    except Exception:
        pass
    return None


async def _cache_embedding(query: str, embedding: list[float]) -> None:
    r = _get_redis()
    if not r:
        return
    try:
        cache_key = f"embed:{hashlib.md5(query.encode()).hexdigest()}"
        await r.setex(cache_key, 86400, json.dumps(embedding))
        await r.close()
    except Exception:
        pass


def _build_fulltext_query(search: str) -> str:
    """Convert search terms to PostgreSQL tsquery format."""
    terms = re.findall(r"\w+", search.lower())
    if not terms:
        return ""
    return " & ".join(f"{term}:*" for term in terms[:10])


def _build_boolean_tsquery(expr: BooleanExpr | SearchTerm) -> str:
    """Convert boolean expression to PostgreSQL tsquery format."""

    def build_term(term: SearchTerm) -> str:
        value = term.value.lower().strip()
        # Escape special chars
        value = re.sub(r"[&|!():*<>\"]", " ", value)
        words = [w for w in re.findall(r"\w+", value) if w][:5]
        if not words:
            return ""
        if term.is_exact:
            # Exact phrase: group words together
            return "(" + " <-> ".join(words) + ")"
        return " & ".join(f"{w}:*" for w in words)

    def build_expr(e: BooleanExpr | SearchTerm) -> str:
        if isinstance(e, SearchTerm):
            return build_term(e)

        parts = [build_expr(t) for t in e.terms if t]
        parts = [p for p in parts if p]  # Remove empty
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


async def _execute_keyword_search(
    db: AsyncSession, search: str, parsed: ParsedSearch, base_stmt
) -> set[UUID]:
    search = search.strip()

    # Build tsquery
    if parsed.is_boolean and parsed.expression:
        tsquery = _build_boolean_tsquery(parsed.expression)
    else:
        tsquery = _build_fulltext_query(search)

    if tsquery:
        # Use full-text search with tsvector
        stmt = base_stmt.where(Job.search_vector.op("@@")(func.to_tsquery("english", tsquery)))
        result = await db.execute(stmt)
        return {row.id for row in result.scalars().all()}

    # Fallback to ILIKE if tsquery failed
    search_term = f"%{search}%"
    stmt = base_stmt.where(
        or_(
            Job.title.ilike(search_term),
            Job.company.ilike(search_term),
            Job.location.ilike(search_term),
        )
    )
    result = await db.execute(stmt)
    return {row.id for row in result.scalars().all()}


async def _execute_vector_search(
    db: AsyncSession, search: str, parsed: ParsedSearch
) -> list[tuple[UUID, float]]:
    embedding = await _get_cached_embedding(search)
    if embedding is None:
        try:
            embedder = EmbeddingService()
            embedding = await embedder.embed(search)
            await _cache_embedding(search, embedding)
        except RuntimeError:
            return []

    stmt = (
        select(
            Job.id,
            (1 - Job.description_embedding.cosine_distance(embedding)).label("similarity"),
        )
        .where(Job.is_active == True)  # noqa: E712
        .where(Job.description_embedding.isnot(None))
        .where(
            (1 - Job.description_embedding.cosine_distance(embedding)) >= VECTOR_SEARCH_THRESHOLD
        )
        .order_by((1 - Job.description_embedding.cosine_distance(embedding)).desc())
        .limit(VECTOR_LIMIT)
    )

    result = await db.execute(stmt)
    return [(row.id, float(row.similarity)) for row in result.all()]


@router.get("/jobs", response_model=JobListResponse)
@limiter.limit(RATE_LIMITS["jobs_list"])
async def list_jobs(
    request: Request,
    db: AsyncSession = Depends(get_db),
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
    base_stmt = select(Job).where(Job.is_active == True)  # noqa: E712

    preserve_match_order = False
    valid_ids: list[UUID] = []

    if match_ids:
        raw_ids = [value.strip() for value in match_ids.split("|") if value.strip()]
        for raw_id in raw_ids:
            try:
                valid_ids.append(UUID(raw_id))
            except ValueError:
                continue
        if valid_ids:
            preserve_match_order = True
        else:
            valid_ids = []

    keyword_ids: set[UUID] = set()
    vector_results: list[tuple[UUID, float]] = []
    result_order: list[UUID] = []

    if search and search.strip():
        parsed = parse_search_query(search)

        keyword_ids = await _execute_keyword_search(db, search, parsed, base_stmt)

        if not parsed.is_boolean:
            vector_results = await _execute_vector_search(db, search, parsed)

        vector_ids = {vid for vid, _ in vector_results}
        all_ids = keyword_ids | vector_ids

        if all_ids:
            vector_scores = {vid: score for vid, score in vector_results}

            def sort_key(job_id: UUID) -> tuple:
                in_keyword = job_id in keyword_ids
                vector_score = vector_scores.get(job_id, 0.0)
                boost = KEYWORD_BOOST if in_keyword else 0.0
                return (-(vector_score + boost),)

            result_order = sorted(all_ids, key=sort_key)
        elif keyword_ids:
            result_order = list(keyword_ids)

    stmt = base_stmt

    if valid_ids:
        all_job_ids = set(valid_ids)
        if result_order:
            combined = set(result_order) & all_job_ids
            result_order = [jid for jid in valid_ids if jid in combined] + [
                jid for jid in result_order if jid not in all_job_ids
            ]
        else:
            result_order = valid_ids
        stmt = stmt.where(Job.id.in_(valid_ids))
    elif result_order:
        stmt = stmt.where(Job.id.in_(result_order))

    if company:
        companies = [c.strip() for c in company.split("|")]
        stmt = stmt.where(Job.company.in_(companies))

    if location:
        search_locations = [loc.strip() for loc in location.split("|") if loc.strip()]
        if search_locations:
            stmt = stmt.where(or_(*[Job.location.ilike(f"%{loc}%") for loc in search_locations]))

    if category:
        categories = [c.strip() for c in category.split("|")]
        stmt = stmt.where(Job.job_category.in_(categories))

    if visa_sponsored is not None:
        stmt = stmt.where(Job.visa_sponsored == visa_sponsored)

    if f1_friendly is not None:
        stmt = stmt.where(Job.f1_friendly == f1_friendly)

    if job_type:
        if job_type == "internship":
            stmt = stmt.where(Job.title.ilike("%intern%"))
        elif job_type == "part-time":
            stmt = stmt.where(Job.title.ilike("%part%time%"))
        elif job_type == "full-time":
            stmt = stmt.where(Job.title.ilike("%full%time%"))

    if work_mode:
        if work_mode == "remote":
            stmt = stmt.where(or_(Job.title.ilike("%remote%"), Job.location.ilike("%remote%")))
        elif work_mode == "hybrid":
            stmt = stmt.where(or_(Job.title.ilike("%hybrid%"), Job.location.ilike("%hybrid%")))
        elif work_mode == "on-site":
            stmt = stmt.where(or_(Job.title.ilike("%on-site%"), Job.location.ilike("%in-office%")))

    if posted_within:
        now = datetime.now(timezone.utc)
        cutoff = None
        if posted_within == "24h":
            cutoff = now - timedelta(hours=24)
        elif posted_within == "week":
            cutoff = now - timedelta(days=7)
        elif posted_within == "month":
            cutoff = now - timedelta(days=30)
        if cutoff:
            stmt = stmt.where(Job.posted_at >= cutoff)

    if preserve_match_order and valid_ids:
        ordering = case(
            {uid: idx for idx, uid in enumerate(valid_ids)}, value=Job.id, else_=len(valid_ids)
        )
        stmt = stmt.order_by(ordering)
    elif result_order:
        ordering = case(
            {uid: idx for idx, uid in enumerate(result_order)},
            value=Job.id,
            else_=len(result_order),
        )
        stmt = stmt.order_by(ordering)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    items = result.scalars().all()

    return JobListResponse(
        items=[JobResponse.model_validate(job) for job in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/jobs/filters/companies")
@limiter.limit(RATE_LIMITS["filters"])
async def get_companies(request: Request, db: AsyncSession = Depends(get_db)) -> list[str]:
    stmt = select(distinct(Job.company)).where(Job.is_active == True).order_by(Job.company)  # noqa: E712
    result = await db.execute(stmt)
    companies = result.all()
    return [c[0] for c in companies]


@router.get("/jobs/filters/locations")
@limiter.limit(RATE_LIMITS["filters"])
async def get_locations(request: Request, db: AsyncSession = Depends(get_db)) -> list[str]:
    stmt = (
        select(distinct(Job.location))
        .where(Job.is_active == True)  # noqa: E712
        .where(Job.location.isnot(None))
        .order_by(Job.location)
    )
    result = await db.execute(stmt)
    locations = result.all()
    return [loc[0] for loc in locations if loc[0]]


@router.get("/jobs/filters/categories")
@limiter.limit(RATE_LIMITS["filters"])
async def get_categories(request: Request, db: AsyncSession = Depends(get_db)) -> list[str]:
    stmt = (
        select(distinct(Job.job_category))
        .where(Job.is_active == True, Job.job_category != None)  # noqa: E712
        .order_by(Job.job_category)
    )
    result = await db.execute(stmt)
    categories = result.all()
    return [cat[0] for cat in categories if cat[0]]


@router.get("/jobs/{job_id}", response_model=JobResponse)
@limiter.limit(RATE_LIMITS["jobs_detail"])
async def get_job(
    request: Request, job_id: UUID, db: AsyncSession = Depends(get_db)
) -> JobResponse:
    stmt = select(Job).where(Job.id == job_id, Job.is_active == True)  # noqa: E712
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.model_validate(job)
