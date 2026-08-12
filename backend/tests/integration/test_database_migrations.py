"""Integration test verifying Alembic database migrations from an empty database."""

from pathlib import Path

from sqlalchemy import create_engine, inspect

from alembic import command
from alembic.config import Config

MIGRATION_TEST_DB_FILE = Path("test_migration_scratch.db")
MIGRATION_TEST_DB_URL_ASYNC = f"sqlite+aiosqlite:///{MIGRATION_TEST_DB_FILE.resolve()}"
MIGRATION_TEST_DB_URL_SYNC = f"sqlite:///{MIGRATION_TEST_DB_FILE.resolve()}"


def test_migration_lifecycle_from_empty_database() -> None:
    """Verify that Alembic migrations run on a completely empty database to head and downgrade cleanly."""
    if MIGRATION_TEST_DB_FILE.exists():
        try:
            MIGRATION_TEST_DB_FILE.unlink()
        except OSError:
            pass

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", MIGRATION_TEST_DB_URL_ASYNC)

    try:
        # 1. Upgrade from empty database to head
        command.upgrade(alembic_cfg, "head")

        sync_engine = create_engine(MIGRATION_TEST_DB_URL_SYNC)
        inspector = inspect(sync_engine)
        tables = set(inspector.get_table_names())

        expected_tables = {
            "users",
            "models",
            "model_versions",
            "experiments",
            "experiment_configurations",
            "trials",
            "benchmark_runs",
            "benchmark_metrics",
            "optimization_runs",
            "deployments",
            "deployment_events",
            "alembic_version",
        }

        assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"

        # 2. Test Downgrade to base
        command.downgrade(alembic_cfg, "base")
        inspector = inspect(sync_engine)
        post_downgrade_tables = set(inspector.get_table_names())
        assert "users" not in post_downgrade_tables
        assert "models" not in post_downgrade_tables
        assert "benchmark_metrics" not in post_downgrade_tables

        # 3. Upgrade back to head
        command.upgrade(alembic_cfg, "head")
        inspector = inspect(sync_engine)
        reupgraded_tables = set(inspector.get_table_names())
        assert expected_tables.issubset(reupgraded_tables)

        sync_engine.dispose()
    finally:
        if MIGRATION_TEST_DB_FILE.exists():
            try:
                MIGRATION_TEST_DB_FILE.unlink()
            except OSError:
                pass
