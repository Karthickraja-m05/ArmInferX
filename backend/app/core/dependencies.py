"""FastAPI dependency injection providers."""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import ArmServeSettings, settings
from backend.app.core.database import get_db as _get_db
from backend.app.repositories.unit_of_work import UnitOfWork


def get_settings() -> ArmServeSettings:
    """Dependency provider returning global application settings."""
    return settings


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency provider yielding active database session."""
    async for session in _get_db():
        yield session


async def get_uow(
    session: AsyncSession = Depends(get_db),
) -> AsyncGenerator[UnitOfWork, None]:
    """Dependency provider yielding UnitOfWork instance bound to current request session."""
    async with UnitOfWork(session=session) as uow:
        yield uow
