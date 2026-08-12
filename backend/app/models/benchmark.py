"""BenchmarkRun and BenchmarkMetric ORM models."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.experiment import ExperimentRecord
    from backend.app.models.model_registry import ModelVersionRecord


class BenchmarkRunRecord(Base):
    __tablename__ = "benchmark_runs"

    model_version_id: Mapped[Any] = mapped_column(
        ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    experiment_id: Mapped[Any | None] = mapped_column(
        ForeignKey("experiments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    hardware_target: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    runtime_name: Mapped[str] = mapped_column(String(50), nullable=False, default="onnxruntime")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING", index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    model_version: Mapped["ModelVersionRecord"] = relationship(
        "ModelVersionRecord", back_populates="benchmark_runs"
    )
    experiment: Mapped["ExperimentRecord | None"] = relationship(
        "ExperimentRecord", back_populates="benchmark_runs"
    )
    metrics: Mapped[list["BenchmarkMetricRecord"]] = relationship(
        "BenchmarkMetricRecord", back_populates="benchmark_run", cascade="all, delete-orphan"
    )


class BenchmarkMetricRecord(Base):
    __tablename__ = "benchmark_metrics"

    benchmark_run_id: Mapped[Any] = mapped_column(
        ForeignKey("benchmark_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    metadata_info: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    benchmark_run: Mapped["BenchmarkRunRecord"] = relationship(
        "BenchmarkRunRecord", back_populates="metrics"
    )
