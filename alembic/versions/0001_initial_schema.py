"""Initial database schema creation for ArmServe.

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-08-12 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users table
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # 2. models table
    op.create_table(
        "models",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("framework", sa.String(length=50), nullable=False, server_default="ONNX"),
        sa.Column("author", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_models_name"), "models", ["name"], unique=True)

    # 3. model_versions table
    op.create_table(
        "model_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("storage_uri", sa.String(length=512), nullable=True),
        sa.Column("format", sa.String(length=50), nullable=False, server_default="ONNX"),
        sa.Column("quantization", sa.String(length=50), nullable=False, server_default="NONE"),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("compatible_runtimes", sa.JSON(), nullable=False),
        sa.Column("metadata_info", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["model_id"], ["models.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_id", "version", name="uq_model_version"),
    )
    op.create_index(op.f("ix_model_versions_model_id"), "model_versions", ["model_id"], unique=False)

    # 4. experiments table
    op.create_table(
        "experiments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="CREATED"),
        sa.Column("budget", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("constraints", sa.JSON(), nullable=False),
        sa.Column("search_space", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_experiments_name"), "experiments", ["name"], unique=False)
    op.create_index(op.f("ix_experiments_model_version_id"), "experiments", ["model_version_id"], unique=False)
    op.create_index(op.f("ix_experiments_user_id"), "experiments", ["user_id"], unique=False)

    # 5. experiment_configurations table
    op.create_table(
        "experiment_configurations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("experiment_id", sa.Uuid(), nullable=False),
        sa.Column("config_key", sa.String(length=100), nullable=False),
        sa.Column("config_value", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("experiment_id", "config_key", name="uq_exp_config_key"),
    )
    op.create_index(op.f("ix_experiment_configurations_experiment_id"), "experiment_configurations", ["experiment_id"], unique=False)

    # 6. trials table
    op.create_table(
        "trials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("experiment_id", sa.Uuid(), nullable=False),
        sa.Column("trial_number", sa.Integer(), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("benchmark_results", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trials_experiment_id"), "trials", ["experiment_id"], unique=False)

    # 7. benchmark_runs table
    op.create_table(
        "benchmark_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("experiment_id", sa.Uuid(), nullable=True),
        sa.Column("hardware_target", sa.String(length=100), nullable=False),
        sa.Column("runtime_name", sa.String(length=50), nullable=False, server_default="onnxruntime"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_benchmark_runs_experiment_id"), "benchmark_runs", ["experiment_id"], unique=False)
    op.create_index(op.f("ix_benchmark_runs_hardware_target"), "benchmark_runs", ["hardware_target"], unique=False)
    op.create_index(op.f("ix_benchmark_runs_model_version_id"), "benchmark_runs", ["model_version_id"], unique=False)
    op.create_index(op.f("ix_benchmark_runs_status"), "benchmark_runs", ["status"], unique=False)

    # 8. benchmark_metrics table
    op.create_table(
        "benchmark_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("benchmark_run_id", sa.Uuid(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metric_name", sa.String(length=100), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("metadata_info", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["benchmark_run_id"], ["benchmark_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_benchmark_metrics_benchmark_run_id"), "benchmark_metrics", ["benchmark_run_id"], unique=False)
    op.create_index(op.f("ix_benchmark_metrics_metric_name"), "benchmark_metrics", ["metric_name"], unique=False)
    op.create_index(op.f("ix_benchmark_metrics_timestamp"), "benchmark_metrics", ["timestamp"], unique=False)

    # 9. optimization_runs table
    op.create_table(
        "optimization_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("experiment_id", sa.Uuid(), nullable=False),
        sa.Column("strategy", sa.String(length=50), nullable=False, server_default="TPE"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("best_trial_id", sa.Uuid(), nullable=True),
        sa.Column("trials_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_trials", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_optimization_runs_experiment_id"), "optimization_runs", ["experiment_id"], unique=False)
    op.create_index(op.f("ix_optimization_runs_status"), "optimization_runs", ["status"], unique=False)

    # 10. deployments table
    op.create_table(
        "deployments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("environment", sa.String(length=50), nullable=False, server_default="development"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("endpoint_url", sa.String(length=512), nullable=True),
        sa.Column("replicas", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["model_version_id"], ["model_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_deployments_name"), "deployments", ["name"], unique=False)
    op.create_index(op.f("ix_deployments_model_version_id"), "deployments", ["model_version_id"], unique=False)
    op.create_index(op.f("ix_deployments_status"), "deployments", ["status"], unique=False)

    # 11. deployment_events table
    op.create_table(
        "deployment_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("deployment_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False, server_default="INFO"),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["deployment_id"], ["deployments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_deployment_events_deployment_id"), "deployment_events", ["deployment_id"], unique=False)
    op.create_index(op.f("ix_deployment_events_event_type"), "deployment_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_deployment_events_timestamp"), "deployment_events", ["timestamp"], unique=False)

    # TimescaleDB hypertable setup for PostgreSQL
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
        op.execute("SELECT create_hypertable('benchmark_metrics', 'timestamp', if_not_exists => TRUE);")


def downgrade() -> None:
    op.drop_table("deployment_events")
    op.drop_table("deployments")
    op.drop_table("optimization_runs")
    op.drop_table("benchmark_metrics")
    op.drop_table("benchmark_runs")
    op.drop_table("trials")
    op.drop_table("experiment_configurations")
    op.drop_table("experiments")
    op.drop_table("model_versions")
    op.drop_table("models")
    op.drop_table("users")
