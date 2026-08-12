"""System status, health, readiness, and environment information schemas."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(
        description="Overall system health status", json_schema_extra={"example": "healthy"}
    )
    environment: str = Field(
        description="Operating environment name", json_schema_extra={"example": "development"}
    )
    database: str = Field(
        default="connected",
        description="Database connection status",
        json_schema_extra={"example": "connected"},
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of health check in UTC",
    )


class ReadinessResponse(BaseModel):
    status: str = Field(
        description="Readiness state ('ready' or 'not_ready')",
        json_schema_extra={"example": "ready"},
    )
    database: str = Field(
        description="Database connection status", json_schema_extra={"example": "connected"}
    )
    latency_ms: float | None = Field(
        default=None,
        description="Database ping latency in milliseconds",
        json_schema_extra={"example": 1.25},
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of readiness probe in UTC",
    )
    pool_info: dict[str, Any] | None = Field(
        default=None, description="Database connection pool metrics"
    )


class SystemInfoResponse(BaseModel):
    app_name: str = Field(
        description="Application title", json_schema_extra={"example": "ArmServe API"}
    )
    version: str = Field(
        description="Application semantic version", json_schema_extra={"example": "0.1.0"}
    )
    environment: str = Field(
        description="Deployment environment name", json_schema_extra={"example": "development"}
    )
    api_version: str = Field(
        description="Active API major version", json_schema_extra={"example": "v1"}
    )
    python_version: str = Field(
        description="Python runtime version", json_schema_extra={"example": "3.10.11"}
    )
    platform: str = Field(
        description="Host OS platform name", json_schema_extra={"example": "Windows"}
    )
    architecture: str = Field(
        description="Host CPU architecture", json_schema_extra={"example": "AMD64"}
    )
    database_dialect: str = Field(
        description="Active database engine dialect", json_schema_extra={"example": "sqlite"}
    )
    runtimes_supported: list[str] = Field(description="List of available inference runtimes")
    observability_enabled: bool = Field(
        description="Whether metrics and observability are enabled",
        json_schema_extra={"example": True},
    )


class ConfigValidationRequest(BaseModel):
    env_overrides: dict[str, Any] | None = Field(
        default=None,
        description="Optional environment variable overrides to validate against configuration schema",
    )


class ConfigValidationResponse(BaseModel):
    valid: bool = Field(description="True if configuration passes validation rules")
    environment: str = Field(description="Configuration environment target")
    errors: list[str] = Field(
        default_factory=list, description="Validation failure messages if any"
    )
    config_summary: dict[str, Any] = Field(
        default_factory=dict, description="Sanitized active configuration overview"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of validation in UTC",
    )
