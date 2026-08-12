"""Deployment and DeploymentEvent repositories implementation."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.deployment import DeploymentEventRecord, DeploymentRecord
from backend.app.repositories.base import BaseRepository


class DeploymentRepository(BaseRepository[DeploymentRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DeploymentRecord, session)

    async def list_by_environment(self, environment: str) -> Sequence[DeploymentRecord]:
        """List active deployments in environment."""
        query = (
            select(DeploymentRecord)
            .where(DeploymentRecord.environment == environment)
            .order_by(DeploymentRecord.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()


class DeploymentEventRepository(BaseRepository[DeploymentEventRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DeploymentEventRecord, session)

    async def list_events_for_deployment(
        self, deployment_id: UUID | str
    ) -> Sequence[DeploymentEventRecord]:
        """Fetch event audit trail for deployment."""
        query = (
            select(DeploymentEventRecord)
            .where(DeploymentEventRecord.deployment_id == deployment_id)
            .order_by(DeploymentEventRecord.timestamp.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()
