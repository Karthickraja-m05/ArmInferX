"""ArmServe Cost Resource Usage Collector Engine.

Captures, validates, and persists actual measured resource telemetry (CPU, RAM, duration,
requests, tokens, concurrency) associated with specific benchmark runs and configuration IDs.
"""

import json
from pathlib import Path
import time
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger("backend.app.services.cost_resource_collector")

MEASUREMENTS_DIR = Path("storage/cost/measurements")


class ResourceUsageMeasurement(BaseModel):
    measurement_id: str
    benchmark_id: str
    experiment_id: str
    config_id: str
    timestamp: str
    cpu_utilization_pct: float = Field(..., ge=0.0, le=100.0)
    peak_memory_mb: float = Field(..., ge=0.0)
    average_memory_mb: float = Field(..., ge=0.0)
    execution_duration_sec: float = Field(..., ge=0.001)
    total_requests_processed: int = Field(..., ge=1)
    total_tokens_generated: int = Field(..., ge=1)
    concurrency_level: int = Field(default=1, ge=1)
    requests_per_second: float = Field(..., ge=0.0)
    tokens_per_second: float = Field(..., ge=0.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CostResourceCollector:
    """Production Resource Usage Measurement Repository."""

    def __init__(self, target_dir: Path | None = None) -> None:
        self.target_dir = target_dir or MEASUREMENTS_DIR
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def record_resource_usage(
        self,
        benchmark_id: str,
        experiment_id: str,
        config_id: str,
        cpu_utilization_pct: float,
        peak_memory_mb: float,
        average_memory_mb: float,
        execution_duration_sec: float,
        total_requests_processed: int,
        total_tokens_generated: int,
        concurrency_level: int = 1,
        metadata: dict[str, Any] | None = None,
    ) -> ResourceUsageMeasurement:
        """Record and persist actual measured hardware & inference telemetry."""
        m_id = f"meas-{int(time.time())}"
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ")

        rps = round(total_requests_processed / max(0.001, execution_duration_sec), 2)
        tps = round(total_tokens_generated / max(0.001, execution_duration_sec), 2)

        measurement = ResourceUsageMeasurement(
            measurement_id=m_id,
            benchmark_id=benchmark_id,
            experiment_id=experiment_id,
            config_id=config_id,
            timestamp=now_str,
            cpu_utilization_pct=round(cpu_utilization_pct, 2),
            peak_memory_mb=round(peak_memory_mb, 2),
            average_memory_mb=round(average_memory_mb, 2),
            execution_duration_sec=round(execution_duration_sec, 3),
            total_requests_processed=total_requests_processed,
            total_tokens_generated=total_tokens_generated,
            concurrency_level=concurrency_level,
            requests_per_second=rps,
            tokens_per_second=tps,
            metadata=metadata or {},
        )

        out_file = self.target_dir / f"{m_id}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(measurement.model_dump_json(indent=2))

        logger.info("Recorded resource usage measurement", m_id=m_id, benchmark_id=benchmark_id, config_id=config_id)
        return measurement

    def get_measurement(self, measurement_id: str) -> ResourceUsageMeasurement | None:
        """Retrieve measurement record by ID."""
        f_path = self.target_dir / f"{measurement_id}.json"
        if not f_path.exists():
            matches = list(self.target_dir.glob(f"*{measurement_id}*.json"))
            if not matches:
                return None
            f_path = matches[0]

        with open(f_path, encoding="utf-8") as f:
            return ResourceUsageMeasurement(**json.load(f))
