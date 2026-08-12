"""Health check schemas."""

from pydantic import BaseModel

from backend.app.schemas.system import HealthResponse, ReadinessResponse


class SystemHealthResponse(BaseModel):
    status: str
    environment: str
    version: str
    database: str
    redis: str


__all__ = ["HealthResponse", "ReadinessResponse", "SystemHealthResponse"]
