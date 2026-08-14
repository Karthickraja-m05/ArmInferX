"""ArmServe System & Inference Telemetry Metrics Collection Engine."""

import time

import psutil
import structlog
from pydantic import BaseModel

from backend.app.core.config import settings

logger = structlog.get_logger("backend.app.services.metrics_collector")


class SystemMetricsSnapshot(BaseModel):
    timestamp: str
    cpu_utilization_percent: float
    memory_used_mb: float
    memory_utilization_percent: float
    disk_used_gb: float
    disk_utilization_percent: float
    net_bytes_sent_kb: float
    net_bytes_recv_kb: float


class RuntimeMetricsSnapshot(BaseModel):
    timestamp: str
    active_model: str
    context_size: int
    thread_count: int
    batch_size: int
    temperature: float


class InferenceMetricsSnapshot(BaseModel):
    timestamp: str
    time_to_first_token_ms: float
    total_latency_ms: float
    prompt_processing_time_ms: float
    generation_time_ms: float
    tokens_per_second: float
    requests_per_second: float
    prompt_tokens: int
    completion_tokens: int


class CompleteMetricsSnapshot(BaseModel):
    timestamp: str
    run_id: str
    system: SystemMetricsSnapshot
    runtime: RuntimeMetricsSnapshot
    inference: InferenceMetricsSnapshot


class MetricsCollector:
    """Collects actual runtime, system, and inference telemetry."""

    @staticmethod
    def capture_system_metrics() -> SystemMetricsSnapshot:
        """Capture live system CPU, RAM, Disk, and Network metrics."""
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        cpu_pct = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        net = psutil.net_io_counters()

        return SystemMetricsSnapshot(
            timestamp=now_str,
            cpu_utilization_percent=round(cpu_pct, 2),
            memory_used_mb=round(mem.used / (1024 * 1024), 2),
            memory_utilization_percent=round(mem.percent, 2),
            disk_used_gb=round(disk.used / (1024 * 1024 * 1024), 2),
            disk_utilization_percent=round(disk.percent, 2),
            net_bytes_sent_kb=round(net.bytes_sent / 1024, 2),
            net_bytes_recv_kb=round(net.bytes_recv / 1024, 2),
        )

    @staticmethod
    def capture_runtime_metrics(
        active_model: str = "qwen2.5-0.5b-instruct",
    ) -> RuntimeMetricsSnapshot:
        """Capture active inference runtime settings."""
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        return RuntimeMetricsSnapshot(
            timestamp=now_str,
            active_model=active_model,
            context_size=settings.runtime.context_length,
            thread_count=settings.runtime.thread_count,
            batch_size=settings.runtime.batch_size,
            temperature=settings.runtime.temperature,
        )

    @classmethod
    def capture_full_snapshot(
        self,
        run_id: str,
        latency_ms: float,
        ttft_ms: float,
        prompt_tokens: int,
        completion_tokens: int,
        active_model: str = "qwen2.5-0.5b-instruct",
    ) -> CompleteMetricsSnapshot:
        """Construct full telemetry record combining system, runtime, and inference measurements."""
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        sys_snap = self.capture_system_metrics()
        run_snap = self.capture_runtime_metrics(active_model)

        # Prompt processing estimated vs token generation split
        prompt_proc_ms = max(0.5, ttft_ms)
        gen_time_ms = max(0.5, latency_ms - prompt_proc_ms)
        tps = round((completion_tokens / (gen_time_ms / 1000.0)), 2) if gen_time_ms > 0 else 0.0
        rps = round(1000.0 / latency_ms, 2) if latency_ms > 0 else 0.0

        inf_snap = InferenceMetricsSnapshot(
            timestamp=now_str,
            time_to_first_token_ms=round(ttft_ms, 2),
            total_latency_ms=round(latency_ms, 2),
            prompt_processing_time_ms=round(prompt_proc_ms, 2),
            generation_time_ms=round(gen_time_ms, 2),
            tokens_per_second=tps,
            requests_per_second=rps,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        return CompleteMetricsSnapshot(
            timestamp=now_str,
            run_id=run_id,
            system=sys_snap,
            runtime=run_snap,
            inference=inf_snap,
        )
