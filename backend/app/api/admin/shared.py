"""Shared helpers for admin API routers."""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.admin import AdminListResponse, JobClickResponse
from app.models import AdminAuditLog, User

T = TypeVar("T")

VALID_PIPELINE_STEPS = {"discover", "ingest", "delete_inactive", "cleanup", "classify", "embed"}


async def paginate(
    db: AsyncSession,
    *,
    base_query: Select,
    page: int,
    page_size: int,
    mapper: Callable[[Any], T],
    order_by: tuple[Any, ...] = (),
    count_stmt: Select | None = None,
    scalars: bool = False,
) -> AdminListResponse[T]:
    """Count, paginate, and map a query into an ``AdminListResponse``.

    ``base_query`` is counted before ordering, matching the previous inline
    behavior. Set ``scalars`` for entity selects (the mapper receives each ORM
    object); leave it false for joined-row selects (the mapper receives a Row).
    Pass ``count_stmt`` to preserve an efficient hand-written count.
    """
    if count_stmt is None:
        count_stmt = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_stmt)).scalar_one() or 0

    stmt = base_query.order_by(*order_by) if order_by else base_query
    offset = (page - 1) * page_size
    result = await db.execute(stmt.offset(offset).limit(page_size))
    rows = result.scalars().all() if scalars else result.all()

    total_pages = math.ceil(total / page_size) if total > 0 else 1
    return AdminListResponse(
        items=[mapper(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


async def paginate_job_clicks(
    db: AsyncSession, base_query: Select, page: int, page_size: int
) -> AdminListResponse[JobClickResponse]:
    """Count, paginate, and map a JobClick join query to an AdminListResponse.

    The query must select ``JobClick`` plus ``title``, ``company``, ``email``,
    and ``name`` columns; ``apply_url`` is included when the query selects it.
    """

    def _map(row: Any) -> JobClickResponse:
        return JobClickResponse(
            id=row.JobClick.id,
            job_id=row.JobClick.job_id,
            job_title=row.title,
            company=row.company,
            apply_url=getattr(row, "apply_url", None),
            user_id=row.JobClick.user_id,
            user_email=row.email,
            user_name=row.name,
            clicked_at=row.JobClick.clicked_at,
            utm_source=row.JobClick.utm_source,
            utm_medium=row.JobClick.utm_medium,
            utm_campaign=row.JobClick.utm_campaign,
        )

    return await paginate(
        db, base_query=base_query, page=page, page_size=page_size, mapper=_map
    )


async def _add_admin_audit_log(
    db: AsyncSession,
    *,
    actor_user_id: UUID | None,
    action: str,
    target_type: str,
    target_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    actor_email = None
    if actor_user_id is not None:
        actor = await db.get(User, actor_user_id)
        actor_email = actor.email if actor else None
    db.add(
        AdminAuditLog(
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata_=metadata or {},
        )
    )
