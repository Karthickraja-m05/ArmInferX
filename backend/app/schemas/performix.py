"""Pydantic schemas for Arm Performix integration, correlation, and evidence generation."""

from typing import Literal

from pydantic import BaseModel, Field


class PerformixRunRequest(BaseModel):
    model_id: str = Field(default="qwen2.5-0.5b-instruct")
    thread_count: int = Field(default=8, ge=1, le=64)
    batch_size: int = Field(default=32, ge=1, le=512)
    context_length: int = Field(default=2048, ge=128, le=8192)
    iterations: int = Field(default=10, ge=1, le=100)
    experiment_id: str | None = Field(default=None)
    deployment_id: str | None = Field(default=None)


class PerformixRunResult(BaseModel):
    performix_run_id: str
    model_id: str
    thread_count: int
    batch_size: int
    context_length: int
    iterations: int
    latency_p50_ms: float
    latency_p90_ms: float
    latency_p99_ms: float
    ttft_ms: float
    tokens_per_second: float
    requests_per_second: float
    cpu_percent: float
    memory_used_mb: float
    execution_status: str
    retry_count: int
    hardware_target: str
    experiment_id: str | None = None
    deployment_id: str | None = None
    timestamp: str


class MetricComparison(BaseModel):
    metric_name: str
    armserve_value: float
    performix_value: float
    difference: float
    variance_percent: float
    consistency_percent: float
    rating: str


class PerformixComparisonResult(BaseModel):
    armserve_run_id: str
    performix_run_id: str
    model_id: str
    hardware_target: str
    metrics_comparison: list[MetricComparison]
    overall_variance_percent: float
    overall_consistency_score: float
    verdict: str
    timestamp: str


class EvidenceReport(BaseModel):
    report_id: str
    format: Literal["markdown", "json", "csv"]
    content: str
    generated_at: str
    baseline_latency_p50_ms: float
    optimized_latency_p50_ms: float
    performance_gain_percent: float
    performix_validated: bool
