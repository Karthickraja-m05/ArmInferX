"""Pydantic schemas for Deployment Engine, Versioning, Health, Monitoring, and Configuration Management."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DeploymentCreateRequest(BaseModel):
    name: str = Field(
        ..., description="Deployment release name", json_schema_extra={"example": "qwen2.5-prod-v1"}
    )
    model_version_id: str | UUID = Field(
        ...,
        description="Target model version ID or key",
        json_schema_extra={"example": "qwen2.5-0.5b-instruct"},
    )
    configuration: dict[str, Any] = Field(
        default_factory=dict,
        description="Runtime parameter configuration (threads, batch_size, context_length, temp, etc.)",
    )
    environment: str = Field(
        default="production",
        description="Deployment environment (production, staging, development)",
    )
    replicas: int = Field(default=1, description="Number of worker replicas")
    runtime_version: str = Field(default="1.0.0-arm64", description="ArmServe runtime version tag")


class DeploymentEventResponse(BaseModel):
    id: UUID | str = Field(..., description="Deployment event record UUID")
    deployment_id: UUID | str = Field(..., description="Parent deployment ID")
    event_type: str = Field(..., description="Event classification (INFO, WARN, ERROR, ROLLBACK)")
    message: str = Field(..., description="Audit message detail")
    details: dict[str, Any] | None = Field(default=None, description="Optional metadata payload")
    timestamp: datetime = Field(..., description="Event timestamp UTC")


class DeploymentResponse(BaseModel):
    id: UUID | str = Field(..., description="Deployment UUID")
    name: str = Field(..., description="Deployment name")
    model_version_id: str | UUID = Field(..., description="Associated model version ID")
    environment: str = Field(..., description="Environment target")
    status: str = Field(
        ...,
        description="Deployment state (PENDING, STAGING, VERIFYING, ACTIVE, ROLLED_BACK, FAILED)",
    )
    endpoint_url: str | None = Field(default=None, description="Production API endpoint URL")
    replicas: int = Field(..., description="Replica count")
    configuration: dict[str, Any] = Field(..., description="Configuration manifest payload")
    deployment_version: str = Field(
        ..., description="Semantic deployment release version (e.g. v1.0.0)"
    )
    runtime_version: str = Field(..., description="ArmServe runtime engine version")
    config_version: str = Field(..., description="SHA-256 configuration hash version key")
    is_active: bool = Field(..., description="True if currently active production deployment")
    health_status: str = Field(
        ..., description="Health status (HEALTHY, DEGRADED, UNHEALTHY, UNKNOWN)"
    )
    metrics_summary: dict[str, Any] = Field(
        default_factory=dict, description="Latest runtime metrics summary"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class DeploymentRollbackRequest(BaseModel):
    reason: str | None = Field(
        default="Manual rollback triggered by operator.", description="Rollback justification"
    )


class DeploymentRollbackResponse(BaseModel):
    success: bool = Field(..., description="True if rollback completed cleanly")
    restored_deployment_id: UUID | str = Field(
        ..., description="ID of restored previous working deployment"
    )
    rolled_back_deployment_id: UUID | str = Field(
        ..., description="ID of rolled-back failing deployment"
    )
    message: str = Field(..., description="Rollback outcome message")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of rollback event",
    )


class StageVerificationDetail(BaseModel):
    stage: str = Field(
        ..., description="Stage name (startup, model_loading, inference, endpoint, resource)"
    )
    passed: bool = Field(..., description="Stage pass/fail boolean")
    duration_ms: float = Field(..., description="Probe duration in milliseconds")
    details: str = Field(..., description="Detail message or diagnostic")


class DeploymentHealthCheckResponse(BaseModel):
    deployment_id: UUID | str = Field(..., description="Target deployment ID")
    status: str = Field(..., description="Overall health state (HEALTHY, DEGRADED, UNHEALTHY)")
    is_healthy: bool = Field(..., description="True if all verification probes passed")
    startup_check: StageVerificationDetail = Field(..., description="Startup verification detail")
    model_check: StageVerificationDetail = Field(
        ..., description="Model loading verification detail"
    )
    inference_check: StageVerificationDetail = Field(
        ..., description="Inference token generation check detail"
    )
    endpoint_check: StageVerificationDetail = Field(..., description="Endpoint probe detail")
    resource_check: StageVerificationDetail = Field(
        ..., description="CPU and RAM resource check detail"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Health check timestamp UTC"
    )


class DeploymentAlert(BaseModel):
    alert_id: str = Field(..., description="Unique alert ID")
    code: str = Field(
        ..., description="Alert code (HIGH_LATENCY, HIGH_MEMORY, RUNTIME_FAILURE, ENDPOINT_FAILURE)"
    )
    severity: str = Field(..., description="Severity level (INFO, WARNING, CRITICAL)")
    message: str = Field(..., description="Alert description")
    timestamp: str = Field(..., description="Timestamp ISO string")


class DeploymentMonitoringResponse(BaseModel):
    deployment_id: UUID | str = Field(..., description="Deployment ID")
    request_count: int = Field(..., description="Total requests processed")
    requests_per_second: float = Field(..., description="Current request throughput (RPS)")
    tokens_per_second: float = Field(..., description="Current token generation throughput (TPS)")
    latency_p50_ms: float = Field(..., description="P50 latency in ms")
    latency_p90_ms: float = Field(..., description="P90 latency in ms")
    latency_p99_ms: float = Field(..., description="P99 latency in ms")
    cpu_percent: float = Field(..., description="Host CPU utilization percent")
    memory_mb: float = Field(..., description="Host memory footprint in MB")
    error_rate_percent: float = Field(..., description="Percentage of failed requests")
    availability_percent: float = Field(..., description="Availability percentage (0-100%)")
    active_alerts: list[DeploymentAlert] = Field(
        default_factory=list, description="Currently active monitoring alerts"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Snapshot timestamp UTC"
    )


class ConfigComparisonRequest(BaseModel):
    config1: dict[str, Any] = Field(..., description="First configuration dict")
    config2: dict[str, Any] = Field(..., description="Second configuration dict")


class ConfigDiffItem(BaseModel):
    parameter: str = Field(..., description="Parameter key")
    val1: Any = Field(..., description="Value in config1")
    val2: Any = Field(..., description="Value in config2")
    status: str = Field(..., description="Difference type (MODIFIED, ADDED, REMOVED)")


class ConfigComparisonResponse(BaseModel):
    config1_hash: str = Field(..., description="SHA-256 hash of config1")
    config2_hash: str = Field(..., description="SHA-256 hash of config2")
    match: bool = Field(..., description="True if configurations are identical")
    differences: list[ConfigDiffItem] = Field(
        default_factory=list, description="List of parameter differences"
    )
