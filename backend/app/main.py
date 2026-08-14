"""ArmServe FastAPI Application Entry Point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.api.root_health import router as root_health_router
from backend.app.api.v1.agent import router as agent_root_router
from backend.app.api.v1.benchmarks import router as benchmarks_root_router
from backend.app.api.v1.deployment import router as deployment_root_router
from backend.app.api.v1.experiments import router as experiments_root_router
from backend.app.api.v1.health import probe_router
from backend.app.api.v1.openai_api import router as openai_root_router
from backend.app.api.v1.operational import router as operational_root_router
from backend.app.api.v1.performix import router as performix_root_router
from backend.app.api.v1.router import api_v1_router
from backend.app.api.v1.runtime import router as runtime_root_router
from backend.app.core.config import settings
from backend.app.core.database import close_db, init_db
from backend.app.core.errors import (
    db_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from backend.app.core.logging import configure_logging, logger
from backend.app.core.middleware import (
    MaintenanceModeMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from backend.app.core.reliability import workflow_recovery_manager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle."""
    configure_logging()
    logger.info(
        "ArmServe API Starting",
        env=settings.app.env,
        debug=settings.app.debug,
        port=settings.app.api_port,
    )

    # Initialize database connection pool on startup unless in test mode (managed by pytest fixtures)
    if settings.app.env.value != "test":
        await init_db()

    # Ensure dataset manager seeds initial quality evaluation datasets if fresh
    from backend.app.services.quality_dataset_manager import QualityDatasetManager

    QualityDatasetManager()

    # Ensure deployment manager has active deployment initialized
    from backend.app.services.deployment_version_manager import deployment_version_manager

    deployment_version_manager._seed_initial_deployment_if_empty()

    # Recover interrupted background workflows on service restart
    workflow_recovery_manager.recover_and_resume_workflows()

    yield

    # Cleanly close database connections on shutdown
    logger.info("ArmServe API Shutting Down")
    await close_db()


app = FastAPI(
    title="ArmServe API",
    description="Autonomous AI Inference Optimization and Deployment Platform for Arm64 Infrastructure",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

# Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# Custom Request Logging Middleware
app.add_middleware(RequestLoggingMiddleware)

# Maintenance Mode Middleware
app.add_middleware(MaintenanceModeMiddleware)

# CORS Middleware (Configurable via settings / environment)
cors_origins = ["*"] if settings.app.debug else settings.app.cors_origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
)

# Global Exception Handlers for Structured Error Responses
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, db_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include Routers
app.include_router(probe_router)
app.include_router(root_health_router)
app.include_router(api_v1_router)
app.include_router(openai_root_router)
app.include_router(runtime_root_router)
app.include_router(benchmarks_root_router)
app.include_router(experiments_root_router)
app.include_router(agent_root_router)
app.include_router(deployment_root_router)
app.include_router(performix_root_router)
app.include_router(operational_root_router)


@app.api_route("/", methods=["GET", "HEAD"], summary="Root Status Overview")
async def root() -> dict[str, str]:
    return {
        "name": "ArmServe API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
        "info": "/api/v1/system/info",
    }
