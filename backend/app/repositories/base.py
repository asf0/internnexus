"""Base repository with common CRUD operations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Generic, Protocol, TypeVar, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.db import Base

ModelType = TypeVar("ModelType", bound=Base)
ModelFactoryType = TypeVar("ModelFactoryType", bound=Base, covariant=True)


class _ModelFactory(Protocol[ModelFactoryType]):
    def __call__(self, **kwargs: object) -> ModelFactoryType: ...


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

    async def create(self, **kwargs: object) -> ModelType:
        """Create a new record."""
        model_factory = cast(_ModelFactory[ModelType], self.model)
        instance = model_factory(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update(self, instance: ModelType, **kwargs: object) -> ModelType:
        """Update a record."""
        for key, value in cast(Mapping[str, object], kwargs).items():
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
