from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, update

from pipeline.infra.db import AsyncSessionLocal
from pipeline.infra.models import PipelineCommand, PipelineCommandStatus
from pipeline.infra.pipeline_config import get_config


async def claim_next_pending_command() -> PipelineCommand | None:
    async with AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        stale_before = now - timedelta(seconds=get_config().pipeline.command_lease_seconds)
        await session.execute(
            update(PipelineCommand)
            .where(
                PipelineCommand.status == PipelineCommandStatus.running,
                PipelineCommand.started_at < stale_before,
            )
            .values(
                status=PipelineCommandStatus.pending,
                started_at=None,
                error_message="Recovered after command lease expired",
            )
        )
        result = await session.execute(
            select(PipelineCommand)
            .where(PipelineCommand.status == PipelineCommandStatus.pending)
            .order_by(PipelineCommand.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        command = result.scalar_one_or_none()
        if command is None:
            await session.rollback()
            return None

        command.status = PipelineCommandStatus.running
        command.started_at = now
        command.error_message = None
        await session.commit()
        await session.refresh(command)
        session.expunge(command)
        return command


async def _finish_command(command_id, *, status: PipelineCommandStatus, run_id, **values: Any) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(PipelineCommand)
            .where(PipelineCommand.id == command_id)
            .values(
                status=status,
                completed_at=datetime.now(timezone.utc),
                run_id=run_id,
                **values,
            )
        )
        await session.commit()


async def mark_command_completed(command_id, result: dict[str, Any] | None = None, run_id=None) -> None:
    await _finish_command(
        command_id, status=PipelineCommandStatus.completed, run_id=run_id, result=result
    )


async def mark_command_failed(command_id, error: BaseException, run_id=None) -> None:
    await _finish_command(
        command_id, status=PipelineCommandStatus.failed, run_id=run_id, error_message=str(error)
    )
