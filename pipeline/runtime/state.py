from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.infra.db import AsyncSessionLocal
from pipeline.infra.models import PipelineRun, PipelineRunStatus

logger = logging.getLogger(__name__)


class PipelineStateManager:
    def __init__(self, run_id: UUID | None = None):
        self.run_id = run_id
        self._session: AsyncSession | None = None

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("PipelineStateManager session not initialized")
        return self._session

    @property
    def session(self) -> AsyncSession:
        """Return the run-scoped session while the manager is active."""
        return self._require_session()

    async def __aenter__(self) -> PipelineStateManager:
        session = AsyncSessionLocal()
        await session.__aenter__()
        self._session = session
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        if self._session:
            await self._session.__aexit__(exc_type, exc_val, exc_tb)
            self._session = None

    async def start_run(self) -> UUID:
        session = self._require_session()
        if self.run_id:
            run = await session.get(PipelineRun, self.run_id)
            if run:
                if run.status == PipelineRunStatus.failed:
                    await session.execute(
                        update(PipelineRun)
                        .where(PipelineRun.id == self.run_id)
                        .values(
                            status=PipelineRunStatus.running,
                            error_message=None,
                            error_step=None,
                            completed_at=None,
                        )
                    )
                    await session.commit()
                    logger.info("Resumed failed pipeline run: %s", self.run_id)
                return self.run_id

        run = PipelineRun(status=PipelineRunStatus.running)
        session.add(run)
        await session.flush()  # Flush to get the ID without committing
        self.run_id = run.id
        await session.commit()
        logger.info(f"Started pipeline run: {self.run_id}")
        return self.run_id

    async def mark_step_complete(self, step: str, results: dict[str, Any] | None = None) -> None:
        if not self.run_id:
            return

        session = self._require_session()

        values: dict[str, Any] = {"step_completed": step}
        if results is not None:
            run = await session.get(PipelineRun, self.run_id)
            persisted: dict[str, Any] = {}
            if run and run.results:
                try:
                    persisted = json.loads(run.results)
                except (TypeError, json.JSONDecodeError):
                    persisted = {}
            persisted.update(results)
            values["results"] = json.dumps(persisted)

        await session.execute(update(PipelineRun).where(PipelineRun.id == self.run_id).values(**values))
        await session.commit()
        logger.debug(f"Marked step '{step}' complete for run {self.run_id}")

    async def mark_completed(self, results: dict[str, Any] | None = None) -> None:
        if not self.run_id:
            return

        session = self._require_session()

        await session.execute(
            update(PipelineRun)
            .where(PipelineRun.id == self.run_id)
            .values(
                status=PipelineRunStatus.completed,
                completed_at=datetime.now(timezone.utc),
                results=json.dumps(results) if results else None,
            )
        )
        await session.commit()
        logger.info(f"Pipeline run {self.run_id} completed successfully")

    async def mark_failed(self, error: Exception, step: str) -> None:
        if not self.run_id:
            return

        session = self._require_session()

        await session.execute(
            update(PipelineRun)
            .where(PipelineRun.id == self.run_id)
            .values(
                status=PipelineRunStatus.failed,
                error_message=str(error),
                error_step=step,
                completed_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()
        logger.error(f"Pipeline run {self.run_id} failed at step '{step}': {error}")

    async def get_last_incomplete_run(self) -> PipelineRun | None:
        session = self._require_session()
        result = await session.execute(
            select(PipelineRun)
            .where(PipelineRun.status == PipelineRunStatus.running)
            .order_by(PipelineRun.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_resumable_run(self, run_id: UUID | None = None) -> PipelineRun | None:
        """Return an explicitly requested or latest running/failed run."""
        session = self._require_session()
        query = select(PipelineRun).where(PipelineRun.status.in_((PipelineRunStatus.running, PipelineRunStatus.failed)))
        if run_id is not None:
            query = query.where(PipelineRun.id == run_id)
        else:
            query = query.order_by(PipelineRun.started_at.desc()).limit(1)
        result = await session.execute(query)
        return result.scalar_one_or_none()

async def get_incomplete_run() -> PipelineRun | None:
    async with PipelineStateManager() as manager:
        return await manager.get_last_incomplete_run()


async def mark_unresumable_run_failed(run_id: UUID, reason: str) -> None:
    """Fail a running row whose persisted step cannot be resumed."""
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(PipelineRun)
            .where(PipelineRun.id == run_id)
            .where(PipelineRun.status == PipelineRunStatus.running)
            .values(
                status=PipelineRunStatus.failed,
                error_message=f"Recovery failed: {reason}",
                error_step="recovery",
                completed_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()


async def get_last_completed_run_started_at() -> datetime | None:
    """Start time of the most recent successfully completed run.

    Used to scope cleanup's raw normalization UPDATEs to rows that could
    have changed since the previous full pass.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PipelineRun.started_at)
            .where(PipelineRun.status == PipelineRunStatus.completed)
            .order_by(PipelineRun.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


async def get_resumable_run(run_id: UUID | None = None) -> PipelineRun | None:
    async with PipelineStateManager() as manager:
        return await manager.get_resumable_run(run_id)


async def clear_incomplete_runs() -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            update(PipelineRun)
            .where(PipelineRun.status == PipelineRunStatus.running)
            .values(
                status=PipelineRunStatus.failed,
                error_message="Cleared by user",
                completed_at=datetime.now(timezone.utc),
            )
            .returning(PipelineRun.id)
        )
        rows = result.fetchall()
        await session.commit()
        return len(rows)
