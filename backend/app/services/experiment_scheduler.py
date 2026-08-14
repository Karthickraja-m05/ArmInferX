"""ArmServe Experiment Scheduling & Queue Management Engine.

Enqueues experiment configurations, prevents conflicting concurrent runs, executes workloads
sequentially with resource safety, tracks retry attempts, and reports real-time queue status.
"""

import asyncio
import time
from collections import deque
from typing import Literal

import structlog
from pydantic import BaseModel

from backend.app.services.experiment_executor import ExperimentExecutor, ExperimentRunRecord

logger = structlog.get_logger("backend.app.services.experiment_scheduler")


class SchedulerStatusResponse(BaseModel):
    queue_status: Literal["IDLE", "RUNNING", "PAUSED"]
    current_experiment: str | None = None
    pending_count: int
    completed_count: int
    failed_count: int
    pending_configs: list[str]
    recent_events: list[str]


class ExperimentScheduler:
    """Production Sequential & Resource-Safe Experiment Scheduler."""

    _instance: "ExperimentScheduler | None" = None
    _initialized: bool = False

    def __new__(cls) -> "ExperimentScheduler":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self.queue: deque[str] = deque()
        self.current_config_id: str | None = None
        self.status: Literal["IDLE", "RUNNING", "PAUSED"] = "IDLE"
        self.completed_count: int = 0
        self.failed_count: int = 0
        self.scheduling_events: list[str] = []
        self._lock = asyncio.Lock()
        self._executor = ExperimentExecutor()

    def _log_event(self, event_msg: str) -> None:
        """Record timestamped scheduling event log."""
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        entry = f"[{ts}] {event_msg}"
        self.scheduling_events.append(entry)
        if len(self.scheduling_events) > 100:
            self.scheduling_events.pop(0)
        logger.info("Scheduler Event", event_details=event_msg)

    def enqueue_configurations(self, config_ids: list[str]) -> list[str]:
        """Enqueue one or more experiment configuration IDs for execution."""
        enqueued = []
        for cid in config_ids:
            if cid not in self.queue and cid != self.current_config_id:
                self.queue.append(cid)
                enqueued.append(cid)
                self._log_event(
                    f"Enqueued configuration '{cid}' into queue (Position: {len(self.queue)})"
                )

        return enqueued

    def get_status(self) -> SchedulerStatusResponse:
        """Return real-time scheduler queue status."""
        return SchedulerStatusResponse(
            queue_status=self.status,
            current_experiment=self.current_config_id,
            pending_count=len(self.queue),
            completed_count=self.completed_count,
            failed_count=self.failed_count,
            pending_configs=list(self.queue),
            recent_events=self.scheduling_events[-10:],
        )

    async def process_queue(self) -> list[ExperimentRunRecord]:
        """Process all queued experiment configurations sequentially."""
        async with self._lock:
            if self.status == "RUNNING":
                logger.info("Scheduler already processing queue")
                return []

            self.status = "RUNNING"
            self._log_event("Started experiment queue processing loop.")
            processed_records: list[ExperimentRunRecord] = []

            try:
                while self.queue:
                    config_id = self.queue.popleft()
                    self.current_config_id = config_id
                    self._log_event(f"Starting execution of config '{config_id}'")

                    try:
                        record = await self._executor.execute_experiment(config_id)
                        if record.status == "COMPLETED":
                            self.completed_count += 1
                            self._log_event(
                                f"Successfully completed experiment '{record.experiment_id}' for config '{config_id}'"
                            )
                        else:
                            self.failed_count += 1
                            self._log_event(
                                f"Experiment '{record.experiment_id}' failed: {record.error_message}"
                            )

                        processed_records.append(record)
                    except Exception as err:
                        self.failed_count += 1
                        self._log_event(f"Execution error on config '{config_id}': {err}")

                    self.current_config_id = None

            finally:
                self.status = "IDLE"
                self.current_config_id = None
                self._log_event("Finished processing experiment queue.")

            return processed_records


# Global singleton instance
experiment_scheduler = ExperimentScheduler()
