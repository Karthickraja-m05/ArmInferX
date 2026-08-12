"""Root-level health and readiness API router."""

from datetime import datetime, timezone

from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.core.database import check_database_health
from backend.app.schemas.system import HealthResponse, ReadinessResponse

router = APIRouter(tags=["System Status"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Health Probe",
    description="Returns top-level application liveness status.",
)
async def get_root_health() -> HealthResponse:
    """Return top-level application health probe."""
    return HealthResponse(
        status="healthy",
        environment=settings.app.env,
        timestamp=datetime.now(timezone.utc),
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Application Readiness Probe",
    description="Verifies database connection and infrastructure readiness for serving traffic.",
    responses={
        200: {"model": ReadinessResponse, "description": "System is ready to serve requests"},
        503: {
            "model": ReadinessResponse,
            "description": "System is not ready due to database failure",
        },
    },
)
async def get_root_readiness(response: Response) -> ReadinessResponse | JSONResponse:
    """Check backend database connection readiness."""
    db_health = await check_database_health()
    is_healthy = db_health.get("status") == "healthy"

    readiness = ReadinessResponse(
        status="ready" if is_healthy else "not_ready",
        database="connected" if is_healthy else "disconnected",
        latency_ms=db_health.get("latency_ms"),
        pool_info=db_health.get("pool_info"),
        timestamp=datetime.now(timezone.utc),
    )

    if not is_healthy:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=readiness.model_dump(mode="json"),
        )

    return readiness
