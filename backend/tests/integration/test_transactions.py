"""Integration tests for transaction handling and UnitOfWork boundaries."""

import pytest
from sqlalchemy import select

from backend.app.core import database
from backend.app.models import UserRecord
from backend.app.repositories.unit_of_work import UnitOfWork


@pytest.mark.asyncio
async def test_transaction_commit_persists_data() -> None:
    """Verify that committed transactions persist data to the database."""
    async with database.AsyncSessionLocal() as session:
        async with database.transaction(session):
            user = UserRecord(
                email="commit_test@armserve.io",
                hashed_password="hash",
                full_name="Commit User",
            )
            session.add(user)

    # Re-open session and verify persistence
    async with database.AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserRecord).where(UserRecord.email == "commit_test@armserve.io")
        )
        fetched = result.scalar_one_or_none()
        assert fetched is not None
        assert fetched.full_name == "Commit User"

        # Cleanup
        await session.delete(fetched)
        await session.commit()


@pytest.mark.asyncio
async def test_transaction_rollback_reverts_data() -> None:
    """Verify that rolled back transactions discard pending mutations."""
    async with database.AsyncSessionLocal() as session:
        try:
            async with database.transaction(session):
                user = UserRecord(
                    email="rollback_test@armserve.io",
                    hashed_password="hash",
                    full_name="Rollback User",
                )
                session.add(user)
                await session.flush()
                # Trigger explicit failure inside transaction
                raise RuntimeError("Simulated transaction failure")
        except RuntimeError:
            pass

    # Re-open session and verify data was NOT persisted
    async with database.AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserRecord).where(UserRecord.email == "rollback_test@armserve.io")
        )
        fetched = result.scalar_one_or_none()
        assert fetched is None


@pytest.mark.asyncio
async def test_unit_of_work_transaction_rollback_on_error() -> None:
    """Verify UnitOfWork automatically rolls back on unhandled exceptions."""
    try:
        async with UnitOfWork() as uow:
            user = UserRecord(
                email="uow_error@armserve.io",
                hashed_password="hash",
            )
            await uow.users.create(user)
            raise ValueError("Failure during UnitOfWork execution")
    except ValueError:
        pass

    async with UnitOfWork() as uow:
        fetched = await uow.users.get_by_email("uow_error@armserve.io")
        assert fetched is None
