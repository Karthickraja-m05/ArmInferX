"""ArmServe FastAPI Application Entry Point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.api.root_health import router as root_health_router
from backend.app.api.v1.router import api_v1_router
from backend.app.core.config import settings
from backend.app.core.database import close_db, init_db
from backend.app.core.errors import (
    db_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from backend.app.core.logging import configure_logging, logger
from backend.app.core.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware


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

    # Initialize database connection pool on startup
    await init_db()

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

# CORS Middleware (Restricted origins in non-debug mode)
cors_origins = (
    ["*"]
    if settings.app.debug
    else ["http://localhost:3000", "http://localhost:5173", "https://app.armserve.io"]
)

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

from backend.app.api.v1.openai_api import router as openai_root_router

# Include Routers
app.include_router(root_health_router)
app.include_router(api_v1_router)
app.include_router(openai_root_router)


@app.get("/", summary="Root Status Overview")
async def root() -> dict[str, str]:
    return {
        "name": "ArmServe API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
        "info": "/api/v1/system/info",
    }
