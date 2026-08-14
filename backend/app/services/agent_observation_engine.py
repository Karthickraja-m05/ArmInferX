"""ArmServe Autonomous Agent Observation Engine.

Aggregates complete, unestimated system telemetry (benchmark runs, experiment history,
optimization rankings, quality evaluation reports, cost calculations, system resources)
into structured, immutable state snapshots.
"""

import time
from pathlib import Path
from typing import Any

import psutil
import structlog
from pydantic import BaseModel, Field

from backend.app.core.config import settings

logger = structlog.get_logger("backend.app.services.agent_observation_engine")

OBSERVATIONS_DIR = Path("storage/agent/observations")


class SystemResourceState(BaseModel):
    cpu_count: int
    cpu_percent: float
    memory_total_mb: float
    memory_used_mb: float
    memory_percent: float


class AgentStateSnapshot(BaseModel):
    snapshot_id: str
    timestamp: str
    active_model_id: str
    runtime_configuration: dict[str, Any]
    system_resources: SystemResourceState
    total_experiments_recorded: int
    total_benchmarks_recorded: int
    total_quality_evaluations: int
    total_cost_calculations: int
    recent_experiment_ids: list[str]
    recent_benchmark_ids: list[str]
    latest_quality_score: float | None = None
    latest_cost_per_1m_tokens: float | None = None
    top_ranked_config_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentObservationEngine:
    """Production State Observation Engine for Autonomous Optimization Agent."""

    def __init__(self, target_dir: Path | None = None) -> None:
        self.target_dir = target_dir or OBSERVATIONS_DIR
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def capture_state_snapshot(
        self,
        active_model_id: str = "qwen2.5-0.5b-instruct",
        top_ranked_config_id: str | None = None,
        latest_quality_score: float | None = None,
        latest_cost_per_1m_tokens: float | None = None,
    ) -> AgentStateSnapshot:
        """Capture full state observation snapshot across disk repositories and system diagnostics."""
        self.target_dir.mkdir(parents=True, exist_ok=True)
        obs_id = f"obs-{int(time.time())}"
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ")

        # System resources
        mem = psutil.virtual_memory()
        sys_state = SystemResourceState(
            cpu_count=psutil.cpu_count(logical=True) or 4,
            cpu_percent=psutil.cpu_percent(interval=None),
            memory_total_mb=round(mem.total / (1024 * 1024), 2),
            memory_used_mb=round(mem.used / (1024 * 1024), 2),
            memory_percent=mem.percent,
        )

        # Count disk history manifests
        exp_files = list(Path("storage/experiments").glob("*.json"))
        bench_files = list(Path("storage/benchmarks").glob("*.json"))
        qual_files = list(Path("storage/quality/evaluations").glob("*.json"))
        cost_files = list(Path("storage/cost/calculations").glob("*.json"))

        recent_exp_ids = [
            f.stem for f in sorted(exp_files, key=lambda p: p.stat().st_mtime, reverse=True)[:5]
        ]
        recent_bench_ids = [
            f.stem for f in sorted(bench_files, key=lambda p: p.stat().st_mtime, reverse=True)[:5]
        ]

        runtime_cfg = {
            "model_path": settings.runtime.model_path,
            "thread_count": settings.runtime.thread_count,
            "batch_size": settings.runtime.batch_size,
            "context_length": settings.runtime.context_length,
            "temperature": settings.runtime.temperature,
            "max_tokens": settings.runtime.max_tokens,
            "quantization_variant": getattr(settings.runtime, "quantization_variant", "Q4_K_M"),
        }

        snapshot = AgentStateSnapshot(
            snapshot_id=obs_id,
            timestamp=now_str,
            active_model_id=active_model_id,
            runtime_configuration=runtime_cfg,
            system_resources=sys_state,
            total_experiments_recorded=len(exp_files),
            total_benchmarks_recorded=len(bench_files),
            total_quality_evaluations=len(qual_files),
            total_cost_calculations=len(cost_files),
            recent_experiment_ids=recent_exp_ids,
            recent_benchmark_ids=recent_bench_ids,
            latest_quality_score=latest_quality_score,
            latest_cost_per_1m_tokens=latest_cost_per_1m_tokens,
            top_ranked_config_id=top_ranked_config_id,
        )

        out_file = self.target_dir / f"{obs_id}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(snapshot.model_dump_json(indent=2))

        logger.info(
            "Captured agent observation state snapshot",
            snapshot_id=obs_id,
            exp_count=len(exp_files),
        )
        return snapshot
