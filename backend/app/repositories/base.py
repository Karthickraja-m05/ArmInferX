"""Generic Base Repository implementation."""

from collections.abc import Sequence
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Abstract generic repository providing CRUD and query capabilities for SQLAlchemy models."""

    def __init__(self, model: type[ModelT], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, entity_id: UUID | str) -> ModelT | None:
        """Fetch a single record by primary key."""
        result = await self.session.get(self.model, entity_id)
        return result

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
        order_by: Any = None,
    ) -> Sequence[ModelT]:
        """List records with pagination and filtering."""
        query = select(self.model)

        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.where(getattr(self.model, key) == value)

        if order_by is not None:
            query = query.order_by(order_by)
        else:
            query = query.order_by(self.model.created_at.desc())

        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count total matching records."""
        query = select(func.count()).select_from(self.model)

        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.where(getattr(self.model, key) == value)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def create(self, entity: ModelT) -> ModelT:
        """Add and flush a new record."""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def create_many(self, entities: Sequence[ModelT]) -> Sequence[ModelT]:
        """Add multiple records in batch."""
        self.session.add_all(entities)
        await self.session.flush()
        for entity in entities:
            await self.session.refresh(entity)
        return entities

    async def update(self, entity: ModelT) -> ModelT:
        """Update and flush an existing record."""
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        """Delete an existing record."""
        await self.session.delete(entity)
        await self.session.flush()

    async def delete_by_id(self, entity_id: UUID | str) -> bool:
        """Delete record by ID."""
        entity = await self.get_by_id(entity_id)
        if entity:
            await self.delete(entity)
            return True
        return False
