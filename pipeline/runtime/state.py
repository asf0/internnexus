from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.repositories.sqlalchemy_repo import AsyncSessionLocal, PipelineRun, PipelineRunStatus
from pipeline.runtime.steps import PIPELINE_STEPS

logger = logging.getLogger(__name__)



class PipelineStateManager:
    def __init__(self, run_id: UUID | None = None):
        self.run_id = run_id
        self._session: AsyncSession | None = None

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("PipelineStateManager session not initialized")
        return self._session

    async def __aenter__(self) -> PipelineStateManager:
        self._session = AsyncSessionLocal()
        await self._session.__aenter__()
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

        await session.execute(update(PipelineRun).where(PipelineRun.id == self.run_id).values(step_completed=step))
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

    def get_resume_step(self, run: PipelineRun) -> str | None:
        if not run.step_completed:
            return PIPELINE_STEPS[0]

        try:
            idx = PIPELINE_STEPS.index(run.step_completed)
            if idx < len(PIPELINE_STEPS) - 1:
                return PIPELINE_STEPS[idx + 1]
        except ValueError:
            pass

        return None


async def get_incomplete_run() -> PipelineRun | None:
    async with PipelineStateManager() as manager:
        return await manager.get_last_incomplete_run()


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
