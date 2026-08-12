"""Standardized error response schema."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error_code: str = Field(description="Machine-readable error classification code")
    message: str = Field(description="Human-readable error explanation")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Time at which error occurred in UTC",
    )
    details: dict[str, Any] | list[Any] | None = Field(
        default=None, description="Optional diagnostic context or field validation details"
    )
