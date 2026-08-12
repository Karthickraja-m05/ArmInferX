"""OptimizationRun repository implementation."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.optimization import OptimizationRunRecord
from backend.app.repositories.base import BaseRepository


class OptimizationRunRepository(BaseRepository[OptimizationRunRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(OptimizationRunRecord, session)

    async def list_for_experiment(
        self, experiment_id: UUID | str
    ) -> Sequence[OptimizationRunRecord]:
        """List optimization runs for a given experiment."""
        query = (
            select(OptimizationRunRecord)
            .where(OptimizationRunRecord.experiment_id == experiment_id)
            .order_by(OptimizationRunRecord.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()
