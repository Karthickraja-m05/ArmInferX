"""Database connection management, session pooling, transactions, and health checks."""

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.core.config import settings
from backend.app.core.metrics import metrics_collector


def get_engine_kwargs(url: str) -> dict[str, Any]:
    """Build database engine configuration kwargs depending on database dialect."""
    is_sqlite = url.startswith("sqlite")
    kwargs: dict[str, Any] = {
        "echo": settings.app.debug,
        "future": True,
    }

    if is_sqlite:
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs.update(
            {
                "pool_size": settings.database.pool_size,
                "max_overflow": settings.database.max_overflow,
                "pool_timeout": settings.database.pool_timeout,
                "pool_recycle": settings.database.pool_recycle,
                "pool_pre_ping": settings.database.pool_pre_ping,
            }
        )

    return kwargs


def build_engine(url: str | None = None) -> AsyncEngine:
    db_url = url or settings.database.connection_url
    return create_async_engine(db_url, **get_engine_kwargs(db_url))


engine: AsyncEngine = build_engine()

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db(url: str | None = None) -> AsyncEngine:
    """Initialize or reconfigure the database engine."""
    global engine, AsyncSessionLocal
    if engine is not None:
        await engine.dispose()
    engine = build_engine(url)
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    return engine


async def close_db() -> None:
    """Close engine connections cleanly."""
    global engine
    if engine is not None:
        await engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency generator for FastAPI routes."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def transaction(session: AsyncSession | None = None) -> AsyncGenerator[AsyncSession, None]:
    """Context manager for managing transactions with explicit commit/rollback handling."""
    if session is not None:
        if session.in_transaction():
            async with session.begin_nested():
                yield session
        else:
            async with session.begin():
                yield session
    else:
        async with AsyncSessionLocal() as new_session:
            async with new_session.begin():
                yield new_session


async def check_database_health() -> dict[str, Any]:
    """Perform real database health check, measuring connection latency and pool metrics."""
    start_time = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            val = result.scalar()
            duration_sec = time.perf_counter() - start_time
            latency_ms = round(duration_sec * 1000, 2)
            db_status = "healthy" if val == 1 else "unhealthy"

            # Record database operation metrics
            metrics_collector.record_db_operation(
                operation="health_check",
                status="success" if db_status == "healthy" else "failure",
                duration_seconds=duration_sec,
            )

            pool_info: dict[str, Any] = {}
            if hasattr(engine.pool, "size"):
                pool_info = {
                    "size": engine.pool.size(),
                    "checked_in": engine.pool.checkedin(),  # type: ignore[attr-defined]
                    "checked_out": engine.pool.checkedout(),  # type: ignore[attr-defined]
                    "overflow": engine.pool.overflow(),  # type: ignore[attr-defined]
                }

            return {
                "status": db_status,
                "database_dialect": engine.dialect.name,
                "latency_ms": latency_ms,
                "pool_info": pool_info,
            }
    except Exception as exc:
        duration_sec = time.perf_counter() - start_time
        latency_ms = round(duration_sec * 1000, 2)

        # Record failed DB operation metric
        metrics_collector.record_db_operation(
            operation="health_check",
            status="error",
            duration_seconds=duration_sec,
        )

        return {
            "status": "unhealthy",
            "database_dialect": engine.dialect.name if engine else "unknown",
            "latency_ms": latency_ms,
            "error": str(exc),
        }
