"""Model and ModelVersion repositories implementation."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.model_registry import ModelRecord, ModelVersionRecord
from backend.app.repositories.base import BaseRepository


class ModelRepository(BaseRepository[ModelRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ModelRecord, session)

    async def get_by_name(self, name: str) -> ModelRecord | None:
        """Fetch model by unique name."""
        query = select(ModelRecord).where(ModelRecord.name == name)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()


class ModelVersionRepository(BaseRepository[ModelVersionRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ModelVersionRecord, session)

    async def get_by_model_and_version(
        self, model_id: UUID | str, version: str
    ) -> ModelVersionRecord | None:
        """Fetch specific version for a model."""
        query = select(ModelVersionRecord).where(
            ModelVersionRecord.model_id == model_id,
            ModelVersionRecord.version == version,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_versions_for_model(self, model_id: UUID | str) -> Sequence[ModelVersionRecord]:
        """List all versions for a given model."""
        query = (
            select(ModelVersionRecord)
            .where(ModelVersionRecord.model_id == model_id)
            .order_by(ModelVersionRecord.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()
