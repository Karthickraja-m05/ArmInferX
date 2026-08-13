"""Deployment Engine, Versioning, Health, and Monitoring REST API Router."""

from typing import Any
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.schemas.deployment import (
    ConfigComparisonRequest,
    ConfigComparisonResponse,
    DeploymentCreateRequest,
    DeploymentEventResponse,
    DeploymentHealthCheckResponse,
    DeploymentMonitoringResponse,
    DeploymentResponse,
    DeploymentRollbackRequest,
    DeploymentRollbackResponse,
)
from backend.app.services.deployment_engine import deployment_engine
from backend.app.services.deployment_monitor import deployment_monitor
from backend.app.services.deployment_version_manager import deployment_version_manager
from backend.app.services.health_service import health_service
from backend.app.services.production_config_manager import production_config_manager

router = APIRouter(prefix="/deployments", tags=["Deployments"])


@router.post(
    "",
    response_model=DeploymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Production Deployment",
    description="Validates configuration, prepares package, loads model, verifies health, and promotes active release.",
)
async def create_deployment(body: DeploymentCreateRequest) -> Any:
    """Create and execute a production deployment."""
    try:
        record = await deployment_engine.execute_deployment(
            name=body.name,
            model_version_id=str(body.model_version_id),
            configuration=body.configuration,
            environment=body.environment,
            replicas=body.replicas,
            runtime_version=body.runtime_version,
        )
        return record
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err),
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deployment execution failed: {str(err)}",
        )


@router.get(
    "",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="List Deployments History",
)
async def list_deployments(
    limit: int = Query(default=20, ge=1, le=100),
    environment: str | None = Query(default=None),
) -> Any:
    """List deployment records with pagination and optional environment filter."""
    all_deps = deployment_version_manager.list_deployment_history(limit=100)
    if environment:
        all_deps = [d for d in all_deps if d.get("environment") == environment]

    paginated = all_deps[:limit]
    return {
        "total_count": len(all_deps),
        "limit": limit,
        "deployments": paginated,
    }


@router.get(
    "/active",
    response_model=DeploymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Currently Active Production Deployment",
)
async def get_active_deployment() -> Any:
    """Return details of currently active deployment."""
    active = deployment_version_manager.get_active_deployment()
    if not active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active deployment found.",
        )
    return active


@router.get(
    "/health",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Deployments Health Verification Summary",
)
async def get_deployments_health(
    limit: int = Query(default=20, ge=1, le=100)
) -> Any:
    """Return recent deployment health verification history and status."""
    history = health_service.get_health_history(limit=limit)
    active = deployment_version_manager.get_active_deployment()
    return {
        "status": "healthy" if (active and active.get("health_status") == "HEALTHY") else "degraded",
        "active_deployment_id": active["id"] if active else None,
        "health_history": history,
    }



@router.get(
    "/{deployment_id}",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Deployment Details and Audit Events",
)
async def get_deployment_details(deployment_id: str) -> Any:
    """Return deployment record and immutable event audit history."""
    all_deps = deployment_version_manager.list_deployment_history(limit=100)
    target = next((d for d in all_deps if d["id"] == str(deployment_id)), None)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment '{deployment_id}' not found.",
        )

    events = deployment_version_manager.list_events_for_deployment(deployment_id)
    return {
        "deployment": target,
        "events": events,
    }


@router.post(
    "/{deployment_id}/rollback",
    response_model=DeploymentRollbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger Deployment Rollback",
    description="Restores the previous working deployment and logs rollback event.",
)
async def rollback_deployment(
    deployment_id: str, body: DeploymentRollbackRequest | None = None
) -> Any:
    """Rollback current deployment to previous working release."""
    reason = body.reason if body else "Operator triggered rollback."
    try:
        restored, curr = deployment_version_manager.execute_rollback(
            current_deployment_id=deployment_id, reason=reason
        )
        return DeploymentRollbackResponse(
            success=True,
            restored_deployment_id=restored["id"],
            rolled_back_deployment_id=curr["id"],
            message=f"Successfully rolled back deployment {curr['id']} to restored version {restored['deployment_version']} ({restored['id']}).",
        )
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rollback failed: {str(err)}",
        )


@router.post(
    "/{deployment_id}/verify",
    response_model=DeploymentHealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute On-Demand Multi-Stage Health Verification",
)
async def verify_deployment_health(deployment_id: str) -> Any:
    """Run 5-stage health verification on deployment."""
    report = await health_service.execute_full_health_verification(deployment_id)
    return DeploymentHealthCheckResponse(
        deployment_id=report.deployment_id,
        status=report.overall_status,
        is_healthy=report.is_healthy,
        startup_check=report.startup_check.model_dump(),
        model_check=report.model_check.model_dump(),
        inference_check=report.inference_check.model_dump(),
        endpoint_check=report.endpoint_check.model_dump(),
        resource_check=report.resource_check.model_dump(),
    )


@router.get(
    "/{deployment_id}/monitoring",
    response_model=DeploymentMonitoringResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Real-Time Monitoring Telemetry",
)
async def get_deployment_monitoring(deployment_id: str) -> Any:
    """Return real-time monitoring metrics and active alerts for deployment."""
    telemetry = deployment_monitor.collect_real_telemetry(deployment_id)
    return telemetry


@router.post(
    "/config/compare",
    response_model=ConfigComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare Two Configurations",
)
async def compare_configurations(body: ConfigComparisonRequest) -> Any:
    """Compare two deployment configurations and return diff payload."""
    diff_res = production_config_manager.compare_configurations(body.config1, body.config2)
    return diff_res
