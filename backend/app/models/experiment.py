"""Experiment, ExperimentConfiguration, and Trial ORM models."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.benchmark import BenchmarkRunRecord
    from backend.app.models.model_registry import ModelVersionRecord
    from backend.app.models.optimization import OptimizationRunRecord
    from backend.app.models.user import UserRecord


class ExperimentRecord(Base):
    __tablename__ = "experiments"

    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    model_version_id: Mapped[Any] = mapped_column(
        ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[Any | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="CREATED")
    budget: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    constraints: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    search_space: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    model_version: Mapped["ModelVersionRecord"] = relationship(
        "ModelVersionRecord", back_populates="experiments"
    )
    user: Mapped["UserRecord | None"] = relationship("UserRecord", back_populates="experiments")
    configurations: Mapped[list["ExperimentConfigurationRecord"]] = relationship(
        "ExperimentConfigurationRecord", back_populates="experiment", cascade="all, delete-orphan"
    )
    trials: Mapped[list["TrialRecord"]] = relationship(
        "TrialRecord", back_populates="experiment", cascade="all, delete-orphan"
    )
    optimization_runs: Mapped[list["OptimizationRunRecord"]] = relationship(
        "OptimizationRunRecord", back_populates="experiment", cascade="all, delete-orphan"
    )
    benchmark_runs: Mapped[list["BenchmarkRunRecord"]] = relationship(
        "BenchmarkRunRecord", back_populates="experiment", cascade="all, delete-orphan"
    )


class ExperimentConfigurationRecord(Base):
    __tablename__ = "experiment_configurations"
    __table_args__ = (UniqueConstraint("experiment_id", "config_key", name="uq_exp_config_key"),)

    experiment_id: Mapped[Any] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    config_key: Mapped[str] = mapped_column(String(100), nullable=False)
    config_value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    experiment: Mapped["ExperimentRecord"] = relationship(
        "ExperimentRecord", back_populates="configurations"
    )


class TrialRecord(Base):
    __tablename__ = "trials"

    experiment_id: Mapped[Any] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trial_number: Mapped[int] = mapped_column(Integer, nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")
    benchmark_results: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    experiment: Mapped["ExperimentRecord"] = relationship(
        "ExperimentRecord", back_populates="trials"
    )
