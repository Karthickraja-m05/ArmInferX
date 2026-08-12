"""BenchmarkRun and BenchmarkMetric repositories implementation."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.benchmark import BenchmarkMetricRecord, BenchmarkRunRecord
from backend.app.repositories.base import BaseRepository


class BenchmarkRunRepository(BaseRepository[BenchmarkRunRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(BenchmarkRunRecord, session)

    async def list_by_hardware(self, hardware_target: str) -> Sequence[BenchmarkRunRecord]:
        """List benchmark runs targeting specified hardware architecture."""
        query = (
            select(BenchmarkRunRecord)
            .where(BenchmarkRunRecord.hardware_target == hardware_target)
            .order_by(BenchmarkRunRecord.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()


class BenchmarkMetricRepository(BaseRepository[BenchmarkMetricRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(BenchmarkMetricRecord, session)

    async def list_for_run(self, benchmark_run_id: UUID | str) -> Sequence[BenchmarkMetricRecord]:
        """Fetch all metrics emitted by a benchmark run."""
        query = (
            select(BenchmarkMetricRecord)
            .where(BenchmarkMetricRecord.benchmark_run_id == benchmark_run_id)
            .order_by(BenchmarkMetricRecord.timestamp.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def add_metrics_batch(
        self, metrics: Sequence[BenchmarkMetricRecord]
    ) -> Sequence[BenchmarkMetricRecord]:
        """Add batch of time-series metric entries."""
        return await self.create_many(metrics)
