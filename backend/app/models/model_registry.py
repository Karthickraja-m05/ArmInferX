"""Model and ModelVersion ORM models."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, BigInteger, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.benchmark import BenchmarkRunRecord
    from backend.app.models.deployment import DeploymentRecord
    from backend.app.models.experiment import ExperimentRecord


class ModelRecord(Base):
    __tablename__ = "models"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    framework: Mapped[str] = mapped_column(String(50), nullable=False, default="ONNX")
    author: Mapped[str | None] = mapped_column(String(100), nullable=True)

    versions: Mapped[list["ModelVersionRecord"]] = relationship(
        "ModelVersionRecord", back_populates="model", cascade="all, delete-orphan"
    )


class ModelVersionRecord(Base):
    __tablename__ = "model_versions"
    __table_args__ = (UniqueConstraint("model_id", "version", name="uq_model_version"),)

    model_id: Mapped[Any] = mapped_column(
        ForeignKey("models.id", ondelete="CASCADE"), index=True, nullable=False
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    storage_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    format: Mapped[str] = mapped_column(String(50), nullable=False, default="ONNX")
    quantization: Mapped[str] = mapped_column(String(50), nullable=False, default="NONE")
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    compatible_runtimes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    metadata_info: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    model: Mapped["ModelRecord"] = relationship("ModelRecord", back_populates="versions")
    experiments: Mapped[list["ExperimentRecord"]] = relationship(
        "ExperimentRecord", back_populates="model_version", cascade="all, delete-orphan"
    )
    benchmark_runs: Mapped[list["BenchmarkRunRecord"]] = relationship(
        "BenchmarkRunRecord", back_populates="model_version", cascade="all, delete-orphan"
    )
    deployments: Mapped[list["DeploymentRecord"]] = relationship(
        "DeploymentRecord", back_populates="model_version", cascade="all, delete-orphan"
    )
