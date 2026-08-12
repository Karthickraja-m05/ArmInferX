"""System health and information API router."""

import platform
import sys

from fastapi import APIRouter, Depends, status

from backend.app.core.config import ArmServeSettings
from backend.app.core.database import check_database_health
from backend.app.core.dependencies import get_settings
from backend.app.schemas.system import (
    ConfigValidationRequest,
    ConfigValidationResponse,
    HealthResponse,
    SystemInfoResponse,
)

router = APIRouter(prefix="/system", tags=["System"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="API v1 System Health",
)
async def get_system_health(
    app_settings: ArmServeSettings = Depends(get_settings),
) -> HealthResponse:
    """Return detailed system health status."""
    db_health = await check_database_health()
    db_status = "connected" if db_health.get("status") == "healthy" else "disconnected"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        environment=app_settings.app.env,
        database=db_status,
    )


@router.get(
    "/info",
    response_model=SystemInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Application & Environment Diagnostics",
    description="Returns real runtime environment details without exposing sensitive secrets or credentials.",
)
async def get_system_info(
    app_settings: ArmServeSettings = Depends(get_settings),
) -> SystemInfoResponse:
    """Return real system environment metadata safely without secret exposure."""
    db_health = await check_database_health()
    db_dialect = str(db_health.get("database_dialect", "unknown"))

    return SystemInfoResponse(
        app_name="ArmServe API",
        version="0.1.0",
        environment=app_settings.app.env,
        api_version="v1",
        python_version=sys.version.split()[0],
        platform=platform.system(),
        architecture=platform.machine(),
        database_dialect=db_dialect,
        runtimes_supported=["onnxruntime"],
        observability_enabled=app_settings.observability.prometheus_enabled,
    )


@router.post(
    "/config/validate",
    response_model=ConfigValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate Configuration",
    description="Validate active or supplied system configuration settings against Pydantic schema rules.",
)
async def validate_system_config(
    body: ConfigValidationRequest | None = None,
    app_settings: ArmServeSettings = Depends(get_settings),
) -> ConfigValidationResponse:
    """Validate system settings and return sanitized configuration status."""
    errors: list[str] = []
    env_name = app_settings.app.env.value

    if body and body.env_overrides:
        try:
            test_settings = ArmServeSettings(**body.env_overrides)
            env_name = test_settings.app.env.value
        except Exception as err:
            errors.append(str(err))

    valid = len(errors) == 0

    summary = {
        "app_env": app_settings.app.env.value,
        "debug": app_settings.app.debug,
        "log_level": app_settings.app.log_level,
        "api_port": app_settings.app.api_port,
        "database_host": app_settings.database.host,
        "database_name": app_settings.database.name,
        "default_runtime": app_settings.inference.default_runtime,
        "max_batch_size": app_settings.inference.max_batch_size,
    }

    return ConfigValidationResponse(
        valid=valid,
        environment=env_name,
        errors=errors,
        config_summary=summary,
    )


@router.get(
    "/config/validate",
    response_model=ConfigValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate Current Configuration",
)
async def validate_current_system_config(
    app_settings: ArmServeSettings = Depends(get_settings),
) -> ConfigValidationResponse:
    """Validate currently loaded system settings."""
    return await validate_system_config(body=None, app_settings=app_settings)
