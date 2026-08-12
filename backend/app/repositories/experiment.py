"""Experiment, ExperimentConfiguration, and Trial repositories implementation."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.experiment import (
    ExperimentConfigurationRecord,
    ExperimentRecord,
    TrialRecord,
)
from backend.app.repositories.base import BaseRepository


class ExperimentRepository(BaseRepository[ExperimentRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ExperimentRecord, session)

    async def get_with_relations(self, experiment_id: UUID | str) -> ExperimentRecord | None:
        """Fetch experiment with eager-loaded configurations and trials."""
        query = (
            select(ExperimentRecord)
            .options(
                selectinload(ExperimentRecord.configurations),
                selectinload(ExperimentRecord.trials),
            )
            .where(ExperimentRecord.id == experiment_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_by_model_version(
        self, model_version_id: UUID | str
    ) -> Sequence[ExperimentRecord]:
        """List experiments associated with a specific model version."""
        query = (
            select(ExperimentRecord)
            .where(ExperimentRecord.model_version_id == model_version_id)
            .order_by(ExperimentRecord.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()


class ExperimentConfigurationRepository(BaseRepository[ExperimentConfigurationRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ExperimentConfigurationRecord, session)

    async def get_by_key(
        self, experiment_id: UUID | str, config_key: str
    ) -> ExperimentConfigurationRecord | None:
        """Fetch single configuration setting by key."""
        query = select(ExperimentConfigurationRecord).where(
            ExperimentConfigurationRecord.experiment_id == experiment_id,
            ExperimentConfigurationRecord.config_key == config_key,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()


class TrialRepository(BaseRepository[TrialRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(TrialRecord, session)

    async def list_for_experiment(self, experiment_id: UUID | str) -> Sequence[TrialRecord]:
        """List all trials for an experiment ordered by trial number."""
        query = (
            select(TrialRecord)
            .where(TrialRecord.experiment_id == experiment_id)
            .order_by(TrialRecord.trial_number.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()
