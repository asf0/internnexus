"""Base repository with common CRUD operations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Generic, TypeVar, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.db import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository providing common database operations."""

    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    def _id_column(self) -> InstrumentedAttribute[UUID]:
        return cast(InstrumentedAttribute[UUID], getattr(self.model, "id"))

    async def get_by_id(self, id: UUID) -> ModelType | None:
        """Get a record by ID."""
        stmt = select(self.model).where(self._id_column() == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[ModelType]:
        """Get all records with pagination."""
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> ModelType:
        """Create a new record."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update(self, instance: ModelType, **kwargs: Any) -> ModelType:
        """Update a record."""
        updates: Mapping[str, Any] = kwargs
        for key, value in updates.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        await self.session.flush()
        return instance

    async def delete(self, instance: ModelType) -> None:
        """Delete a record."""
        await self.session.delete(instance)

    async def refresh(self, instance: ModelType) -> ModelType:
        """Refresh a record from the database."""
        await self.session.refresh(instance)
        return instance
