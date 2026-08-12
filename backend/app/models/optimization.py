"""OptimizationRun ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.experiment import ExperimentRecord


class OptimizationRunRecord(Base):
    __tablename__ = "optimization_runs"

    experiment_id: Mapped[Any] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    strategy: Mapped[str] = mapped_column(String(50), nullable=False, default="TPE")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING", index=True)
    best_trial_id: Mapped[UUID | None] = mapped_column(nullable=True)
    trials_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_trials: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    experiment: Mapped["ExperimentRecord"] = relationship(
        "ExperimentRecord", back_populates="optimization_runs"
    )
