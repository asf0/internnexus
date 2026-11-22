"""One-shot homepage state for a signed-in user.

The homepage needs three independent pieces of user state: the unread
notification count, the saved job ids, and the applied job ids. Fetching them
from three endpoints made the frontend authenticate three times and issue three
separate round trips for one render. This service resolves them in a single
statement; the endpoint still authenticates once.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AppliedJob, SavedJob, UserNotification
from app.schemas.users import HomeStateResponse


class HomeStateService:
    """Read the homepage's user-scoped state in one query."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user_id: UUID) -> HomeStateResponse:
        unread_count = (
            select(func.count(UserNotification.id))
            .where(
                UserNotification.user_id == user_id,
                UserNotification.is_read.is_(False),
            )
            .scalar_subquery()
        )
        saved_job_ids = (
            select(func.array_agg(SavedJob.job_id))
            .where(SavedJob.user_id == user_id)
            .scalar_subquery()
        )
        applied_job_ids = (
            select(func.array_agg(AppliedJob.job_id))
            .where(AppliedJob.user_id == user_id)
            .scalar_subquery()
        )

        row = (await self.session.execute(select(unread_count, saved_job_ids, applied_job_ids))).one()
        return HomeStateResponse(
            unread_count=int(row[0] or 0),
            saved_job_ids=list(row[1] or []),
            applied_job_ids=list(row[2] or []),
        )
