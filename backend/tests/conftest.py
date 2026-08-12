"""Pytest fixtures for integration and database tests."""

import os
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from alembic import command
from alembic.config import Config
from backend.app.core import database
from backend.app.main import app
from backend.app.repositories.unit_of_work import UnitOfWork

TEST_DB_FILE = Path("test_armserve.db")
TEST_DB_URL = os.getenv("TEST_DATABASE_URL", f"sqlite+aiosqlite:///{TEST_DB_FILE.resolve()}")


def run_alembic_upgrade(db_url: str) -> None:
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")


def run_alembic_downgrade(db_url: str) -> None:
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.downgrade(alembic_cfg, "base")


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database_env() -> AsyncGenerator[None, None]:
    """Ensure test database file is cleaned up, migrated, and engine initialized before test session."""
    if TEST_DB_FILE.exists():
        try:
            TEST_DB_FILE.unlink()
        except OSError:
            pass

    os.environ["DATABASE_URL"] = TEST_DB_URL

    # Initialize app core database engine & AsyncSessionLocal for test database
    await database.init_db(TEST_DB_URL)

    # Run migration from empty database to head
    run_alembic_upgrade(TEST_DB_URL)

    yield

    await database.close_db()

    if TEST_DB_FILE.exists():
        try:
            TEST_DB_FILE.unlink()
        except OSError:
            pass


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide clean database session wrapped in a transaction that rollbacks after test."""
    async with database.AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def uow(db_session: AsyncSession) -> AsyncGenerator[UnitOfWork, None]:
    """Provide UnitOfWork using test database session."""
    async with UnitOfWork(session=db_session) as unit_of_work:
        yield unit_of_work


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),  # type: ignore[arg-type]
        base_url="http://testserver",
    ) as ac:
        yield ac
