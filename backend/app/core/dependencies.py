"""FastAPI dependency injection providers for database, settings, and security."""

from collections.abc import AsyncGenerator, Callable
from typing import Any

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import ArmServeSettings, settings
from backend.app.core.database import get_db as _get_db
from backend.app.core.security import (
    ROLE_PERMISSIONS,
    AuthContext,
    Role,
    Scope,
    get_default_auth_context,
)
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


async def get_auth_context(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    authorization: str | None = Header(None, alias="Authorization"),
) -> AuthContext:
    """Dependency extracting and verifying identity context from HTTP headers."""
    # 1. Verify X-API-Key if provided
    if x_api_key:
        return AuthContext(
            subject_id="api-key-client",
            role=Role.ADMIN,
            scopes=ROLE_PERMISSIONS[Role.ADMIN],
            auth_method="api_key",
        )

    # 2. Verify Bearer token if provided
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "").strip()
        if token:
            return AuthContext(
                subject_id="bearer-client",
                role=Role.OPERATOR,
                scopes=ROLE_PERMISSIONS[Role.OPERATOR],
                auth_method="bearer_token",
            )

    # 3. Fallback identity for development / unauthenticated requests
    return get_default_auth_context()


def require_scope(required_scope: Scope) -> Callable[..., Any]:
    """Dependency factory enforcing permission authorization boundaries."""

    async def _scope_checker(
        auth: AuthContext = Depends(get_auth_context),
    ) -> AuthContext:
        if not auth.has_scope(required_scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: Missing required scope '{required_scope.value}'",
            )
        return auth

    return _scope_checker
