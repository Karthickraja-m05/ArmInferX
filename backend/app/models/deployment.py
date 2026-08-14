"""Deployment and DeploymentEvent ORM models."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.model_registry import ModelVersionRecord


class DeploymentRecord(Base):
    __tablename__ = "deployments"

    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_version_id: Mapped[Any] = mapped_column(
        ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    environment: Mapped[str] = mapped_column(String(50), nullable=False, default="development")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING", index=True)
    endpoint_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    replicas: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    deployment_version: Mapped[str] = mapped_column(
        String(50), nullable=False, default="v1.0.0", index=True
    )
    runtime_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0-arm64")
    config_version: Mapped[str] = mapped_column(String(50), nullable=False, default="cfg-v1")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    health_status: Mapped[str] = mapped_column(String(50), nullable=False, default="HEALTHY")
    metrics_summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    model_version: Mapped["ModelVersionRecord"] = relationship(
        "ModelVersionRecord", back_populates="deployments"
    )
    events: Mapped[list["DeploymentEventRecord"]] = relationship(
        "DeploymentEventRecord", back_populates="deployment", cascade="all, delete-orphan"
    )


class DeploymentEventRecord(Base):
    __tablename__ = "deployment_events"

    deployment_id: Mapped[Any] = mapped_column(
        ForeignKey("deployments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, default="INFO", index=True)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    deployment: Mapped["DeploymentRecord"] = relationship(
        "DeploymentRecord", back_populates="events"
    )
