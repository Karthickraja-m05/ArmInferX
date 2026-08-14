"""ArmServe Workload Isolation, Concurrency Limiter, and Job Scheduler.

Enforces resource isolation across concurrent experiments, optimization workflows,
and model deployments while measuring throughput, queue depth, and utilization.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar

import structlog

from backend.app.core.metrics import metrics_collector

logger = structlog.get_logger("backend.app.core.scalability")

T = TypeVar("T")


class WorkloadType(str, Enum):
    EXPERIMENT = "experiment"
    OPTIMIZATION = "optimization"
    DEPLOYMENT = "deployment"
    BENCHMARK = "benchmark"


@dataclass
class JobQueueStats:
    active_jobs: int = 0
    queued_jobs: int = 0
    max_concurrency: int = 10
    total_processed: int = 0
    total_rejected: int = 0
    queue_utilization_percent: float = 0.0


class ConcurrencyLimiter:
    """Resource isolation semaphore for high-concurrency ArmServe workloads."""

    def __init__(self, max_concurrent_jobs: int = 8, max_queue_depth: int = 64):
        self.max_concurrent_jobs = max_concurrent_jobs
        self.max_queue_depth = max_queue_depth
        self._semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self._active_count = 0
        self._queue_count = 0
        self._total_processed = 0
        self._total_rejected = 0
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """Attempt to acquire execution slot with queue depth guarding."""
        async with self._lock:
            if self._queue_count >= self.max_queue_depth:
                self._total_rejected += 1
                logger.warning(
                    "Job rejected due to queue saturation",
                    queued=self._queue_count,
                    max_queue=self.max_queue_depth,
                )
                return False
            self._queue_count += 1

        await self._semaphore.acquire()

        async with self._lock:
            self._queue_count -= 1
            self._active_count += 1
        return True

    def release(self) -> None:
        """Release execution slot after job completion."""
        self._semaphore.release()
        self._active_count = max(0, self._active_count - 1)
        self._total_processed += 1

    def get_stats(self) -> JobQueueStats:
        """Calculate live queue depth and utilization percent."""
        total_capacity = self.max_concurrent_jobs + self.max_queue_depth
        current_load = self._active_count + self._queue_count
        utilization = round((current_load / max(1, total_capacity)) * 100.0, 2)

        return JobQueueStats(
            active_jobs=self._active_count,
            queued_jobs=self._queue_count,
            max_concurrency=self.max_concurrent_jobs,
            total_processed=self._total_processed,
            total_rejected=self._total_rejected,
            queue_utilization_percent=utilization,
        )


class ScalabilityManager:
    """Platform-wide scalability and workload isolation coordinator."""

    def __init__(self) -> None:
        self.limiters: dict[WorkloadType, ConcurrencyLimiter] = {
            WorkloadType.EXPERIMENT: ConcurrencyLimiter(max_concurrent_jobs=4, max_queue_depth=32),
            WorkloadType.OPTIMIZATION: ConcurrencyLimiter(
                max_concurrent_jobs=4, max_queue_depth=32
            ),
            WorkloadType.DEPLOYMENT: ConcurrencyLimiter(max_concurrent_jobs=4, max_queue_depth=32),
            WorkloadType.BENCHMARK: ConcurrencyLimiter(max_concurrent_jobs=8, max_queue_depth=64),
        }

    async def schedule_job(
        self,
        workload_type: WorkloadType,
        job_func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Schedule and execute job within work-isolated concurrency limits."""
        limiter = self.limiters[workload_type]
        acquired = await limiter.acquire()
        if not acquired:
            metrics_collector.record_error(
                error_type="QueueSaturationExceeded",
                status_code=429,
                endpoint=f"workload:{workload_type.value}",
            )
            raise RuntimeError(
                f"Workload queue saturated for {workload_type.value}. Try again later."
            )

        t0 = time.perf_counter()
        try:
            if asyncio.iscoroutinefunction(job_func):
                result = await job_func(*args, **kwargs)
            else:
                result = job_func(*args, **kwargs)
            return result
        finally:
            limiter.release()
            duration = time.perf_counter() - t0
            logger.info(
                "Scheduled job executed",
                workload=workload_type.value,
                duration_seconds=round(duration, 3),
            )

    def get_scalability_metrics(self) -> dict[str, Any]:
        """Return platform workload utilization metrics across all engines."""
        return {
            workload.value: {
                "active_jobs": limiter.get_stats().active_jobs,
                "queued_jobs": limiter.get_stats().queued_jobs,
                "max_concurrency": limiter.get_stats().max_concurrency,
                "total_processed": limiter.get_stats().total_processed,
                "total_rejected": limiter.get_stats().total_rejected,
                "queue_utilization_percent": limiter.get_stats().queue_utilization_percent,
            }
            for workload, limiter in self.limiters.items()
        }


scalability_manager = ScalabilityManager()
