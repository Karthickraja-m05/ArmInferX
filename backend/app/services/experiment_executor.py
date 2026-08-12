"""ArmServe Optimization Experiment Execution Engine.

Applies experiment configurations to runtime, executes Phase 3 benchmark workloads,
captures telemetry, tracks state transitions, and maintains traceable execution manifests.
"""

import asyncio
import json
from pathlib import Path
import time
from typing import Any, Literal

import structlog
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.services.benchmark_runner import BenchmarkConfig, BenchmarkRunResult, BenchmarkRunner
from backend.app.services.experiment_generator import CONFIGS_DIR, ExperimentConfigRecord
from backend.app.services.metrics_collector import CompleteMetricsSnapshot, MetricsCollector
from backend.app.services.runtime_manager import RuntimeManager, runtime_manager

logger = structlog.get_logger("backend.app.services.experiment_executor")

EXPERIMENT_RUNS_DIR = Path("storage/experiments/runs")


class ExperimentRunRecord(BaseModel):
    experiment_id: str
    config_id: str
    status: Literal["PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"] = "PENDING"
    started_at: str | None = None
    completed_at: str | None = None
    model_id: str
    runtime_version: str = "v1.17.1-arm-mlas"
    configuration: dict[str, Any]
    benchmark_run_id: str | None = None
    metrics_summary: dict[str, float] | None = None
    telemetry_snapshot: CompleteMetricsSnapshot | None = None
    execution_logs: list[str] = Field(default_factory=list)
    error_message: str | None = None
    retry_count: int = 0


class ExperimentExecutor:
    """Production Executor for Running Parameter Optimization Experiments."""

    def __init__(self) -> None:
        EXPERIMENT_RUNS_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def load_config(cls, config_id: str) -> ExperimentConfigRecord:
        """Load experiment configuration manifest by ID."""
        file_path = CONFIGS_DIR / f"{config_id}.json"
        if not file_path.exists():
            matches = list(CONFIGS_DIR.glob(f"*{config_id}*.json"))
            if not matches:
                raise ValueError(f"Configuration '{config_id}' not found.")
            file_path = matches[0]

        with open(file_path, encoding="utf-8") as f:
            return ExperimentConfigRecord(**json.load(f))

    def _apply_runtime_configuration(self, config: ExperimentConfigRecord, exp_record: ExperimentRunRecord) -> None:
        """Apply dynamic parameter configuration to active runtime settings."""
        exp_record.execution_logs.append(f"Applying configuration: threads={config.thread_count}, batch={config.batch_size}, temp={config.temperature}")
        logger.info(
            "Applying experiment runtime config",
            config_id=config.config_id,
            threads=config.thread_count,
            batch=config.batch_size,
        )

        # Mutate active settings
        settings.runtime.thread_count = config.thread_count
        settings.runtime.batch_size = config.batch_size
        settings.runtime.context_length = config.context_length
        settings.runtime.temperature = config.temperature
        settings.runtime.max_tokens = config.max_tokens

    async def execute_experiment(self, config_id: str, warmup_iterations: int = 2, benchmark_iterations: int = 5) -> ExperimentRunRecord:
        """Execute complete optimization experiment pipeline with automatic retry."""
        config = self.load_config(config_id)
        exp_id = f"exp-{int(time.time())}"
        start_time_str = time.strftime("%Y-%m-%dT%H:%M:%SZ")

        exp_record = ExperimentRunRecord(
            experiment_id=exp_id,
            config_id=config.config_id,
            status="RUNNING",
            started_at=start_time_str,
            model_id=config.model_id,
            configuration=config.model_dump(),
        )
        exp_record.execution_logs.append(f"Started experiment {exp_id} for config {config.config_id}")

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            exp_record.retry_count = attempt - 1
            try:
                # 1. Apply configuration
                self._apply_runtime_configuration(config, exp_record)

                # 2. Re-verify runtime state
                exp_record.execution_logs.append("Verifying runtime engine readiness...")
                rt_status = runtime_manager.get_runtime_status()
                if rt_status.get("lifecycle_state") != "loaded":
                    exp_record.execution_logs.append("Reloading runtime model...")
                    runtime_manager.load_model(config.model_id)

                # 3. Launch Phase 3 Benchmark Runner
                exp_record.execution_logs.append("Launching Phase 3 benchmark suite...")
                bench_cfg = BenchmarkConfig(
                    model_id=config.model_id,
                    warmup_iterations=warmup_iterations,
                    iterations=benchmark_iterations,
                    concurrency=1,
                    prompt="What ARM64 Neoverse V1 CPU optimizations are used in ArmServe?",
                )
                runner = BenchmarkRunner(bench_cfg)
                bench_result: BenchmarkRunResult = await runner.run_benchmark()

                # 4. Link Experiment -> Benchmark Run -> Metrics
                exp_record.benchmark_run_id = bench_result.run_id
                exp_record.metrics_summary = {
                    "latency_p50_ms": bench_result.latency_p50_ms,
                    "latency_p90_ms": bench_result.latency_p90_ms,
                    "latency_p99_ms": bench_result.latency_p99_ms,
                    "requests_per_second": bench_result.requests_per_second,
                    "tokens_per_second": bench_result.tokens_per_second,
                    "peak_memory_mb": bench_result.peak_memory_mb,
                }

                # 5. Capture Telemetry Snapshot
                exp_record.telemetry_snapshot = MetricsCollector.capture_full_snapshot(
                    run_id=bench_result.run_id,
                    latency_ms=bench_result.latency_p50_ms,
                    ttft_ms=max(1.0, bench_result.latency_min_ms),
                    prompt_tokens=bench_result.total_prompt_tokens,
                    completion_tokens=bench_result.total_completion_tokens,
                    active_model=config.model_id,
                )

                # Mark completed
                exp_record.status = "COMPLETED"
                exp_record.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ")
                exp_record.execution_logs.append(f"Experiment {exp_id} completed successfully (RPS={bench_result.requests_per_second}, P50={bench_result.latency_p50_ms}ms)")

                logger.info(
                    "Experiment executed successfully",
                    exp_id=exp_id,
                    config_id=config.config_id,
                    rps=bench_result.requests_per_second,
                    p50_ms=bench_result.latency_p50_ms,
                )
                break

            except Exception as err:
                logger.warning("Experiment attempt failed", exp_id=exp_id, attempt=attempt, error=str(err))
                exp_record.execution_logs.append(f"Attempt {attempt} failed: {err}")
                if attempt == max_retries:
                    exp_record.status = "FAILED"
                    exp_record.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ")
                    exp_record.error_message = str(err)
                else:
                    await asyncio.sleep(1.0 * (2 ** (attempt - 1)))

        # Save experiment run manifest
        out_file = EXPERIMENT_RUNS_DIR / f"{exp_id}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(exp_record.model_dump_json(indent=2))

        return exp_record

    @classmethod
    def list_experiments(
        cls,
        status_filter: str | None = None,
        model_id_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """List historical experiment runs with filtering by status and model."""
        EXPERIMENT_RUNS_DIR.mkdir(parents=True, exist_ok=True)
        runs = []
        for run_path in sorted(EXPERIMENT_RUNS_DIR.glob("*.json"), reverse=True):
            try:
                with open(run_path, encoding="utf-8") as f:
                    data = json.load(f)

                if status_filter and data.get("status") != status_filter.upper():
                    continue
                if model_id_filter and data.get("model_id") != model_id_filter:
                    continue

                runs.append(data)
            except Exception as err:
                logger.warning("Failed to read experiment run", path=str(run_path), error=str(err))

        return runs
