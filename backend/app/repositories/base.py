"""Base repository with common CRUD operations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.db import Base


class _ModelFactory[TModel: Base](Protocol):
    def __call__(self, **kwargs: object) -> TModel: ...


class BaseRepository[TModel: Base]:
    """Base repository providing common database operations."""

    def __init__(self, model: type[TModel], session: AsyncSession):
        self.model = model
        self.session = session

    def _id_column(self) -> InstrumentedAttribute[UUID]:
        return cast(InstrumentedAttribute[UUID], getattr(self.model, "id"))

    async def get_by_id(self, id: UUID) -> TModel | None:
        """Get a record by ID."""
        stmt = select(self.model).where(self._id_column() == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[TModel]:
        """Get all records with pagination."""
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **kwargs: object) -> TModel:
        """Create a new record."""
        model_factory = cast(_ModelFactory[TModel], self.model)
        instance = model_factory(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update(self, instance: TModel, **kwargs: object) -> TModel:
        """Update a record."""
        for key, value in cast(Mapping[str, object], kwargs).items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        await self.session.flush()
        return instance

    async def delete(self, instance: TModel) -> None:
        """Delete a record."""
        await self.session.delete(instance)

    async def refresh(self, instance: TModel) -> TModel:
        """Refresh a record from the database."""
        await self.session.refresh(instance)
        return instance
