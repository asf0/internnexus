from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update

from pipeline.db import AsyncSessionLocal
from pipeline.models import PipelineCommand, PipelineCommandStatus


async def claim_next_pending_command() -> PipelineCommand | None:
    async with AsyncSessionLocal() as session:
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
        command.started_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(command)
        session.expunge(command)
        return command


async def mark_command_completed(command_id, result: dict[str, Any] | None = None, run_id=None) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(PipelineCommand)
            .where(PipelineCommand.id == command_id)
            .values(
                status=PipelineCommandStatus.completed,
                completed_at=datetime.now(timezone.utc),
                result=result,
                run_id=run_id,
            )
        )
        await session.commit()


async def mark_command_failed(command_id, error: BaseException, run_id=None) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(PipelineCommand)
            .where(PipelineCommand.id == command_id)
            .values(
                status=PipelineCommandStatus.failed,
                completed_at=datetime.now(timezone.utc),
                error_message=str(error),
                run_id=run_id,
            )
        )
        await session.commit()
