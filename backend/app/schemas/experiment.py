"""Experiment schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PerformanceConstraints(BaseModel):
    max_latency_p99_ms: float = Field(gt=0, description="Target p99 latency ceiling in ms")
    min_throughput_rps: float = Field(gt=0, description="Target throughput floor in req/s")
    max_cost_per_1k: float | None = Field(
        default=None, description="Max allowed cost per 1k requests"
    )
    min_quality_score: float | None = Field(
        default=None, description="Minimum acceptable quality score"
    )


class SearchSpace(BaseModel):
    runtimes: list[str] = Field(default_factory=lambda: ["onnxruntime", "llamacpp", "vllm"])
    quantizations: list[str] = Field(default_factory=lambda: ["fp32", "fp16", "int8"])
    instance_types: list[str] = Field(default_factory=lambda: ["c7g.xlarge", "c7g.2xlarge"])
    batch_sizes: list[int] = Field(default_factory=lambda: [1, 2, 4, 8])


class ExperimentCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    name: str = Field(min_length=1, max_length=100)
    model_id: UUID

    constraints: PerformanceConstraints
    search_space: SearchSpace = Field(default_factory=SearchSpace)
    budget: int = Field(default=10, ge=1, le=100)


class TrialResponse(BaseModel):
    id: UUID
    trial_number: int
    configuration: dict[str, Any]
    status: str
    benchmark_results: dict[str, Any] | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ExperimentResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: UUID
    name: str

    status: str
    model_id: UUID
    constraints: dict[str, Any]
    search_space: dict[str, Any]
    budget: int
    created_at: datetime
    updated_at: datetime
    trials: list[TrialResponse] = Field(default_factory=list)
