"""Unit of Work implementation for transaction boundary management across repositories."""

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core import database
from backend.app.repositories.benchmark import BenchmarkMetricRepository, BenchmarkRunRepository
from backend.app.repositories.deployment import DeploymentEventRepository, DeploymentRepository
from backend.app.repositories.experiment import (
    ExperimentConfigurationRepository,
    ExperimentRepository,
    TrialRepository,
)
from backend.app.repositories.model import ModelRepository, ModelVersionRepository
from backend.app.repositories.optimization import OptimizationRunRepository
from backend.app.repositories.user import UserRepository


class UnitOfWork:
    """Encapsulates a database session transaction and repository accessors."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session: AsyncSession | None = session
        self._external_session = session is not None

    async def __aenter__(self) -> "UnitOfWork":
        if self.session is None:
            self.session = database.AsyncSessionLocal()

        self.users = UserRepository(self.session)
        self.models = ModelRepository(self.session)
        self.model_versions = ModelVersionRepository(self.session)
        self.experiments = ExperimentRepository(self.session)
        self.experiment_configurations = ExperimentConfigurationRepository(self.session)
        self.trials = TrialRepository(self.session)
        self.benchmark_runs = BenchmarkRunRepository(self.session)
        self.benchmark_metrics = BenchmarkMetricRepository(self.session)
        self.optimization_runs = OptimizationRunRepository(self.session)
        self.deployments = DeploymentRepository(self.session)
        self.deployment_events = DeploymentEventRepository(self.session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
        if not self._external_session and self.session is not None:
            await self.session.close()

    async def commit(self) -> None:
        if self.session is not None:
            await self.session.commit()

    async def rollback(self) -> None:
        if self.session is not None:
            await self.session.rollback()
