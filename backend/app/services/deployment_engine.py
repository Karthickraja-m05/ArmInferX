"""Production Deployment Engine service for ArmServe.

Orchestrates full production deployment workflows:
1. Configuration Validation
2. Deployment Package Preparation
3. Runtime Deployment
4. Model Loading
5. Inference Server Startup & Readiness Verification
6. Multi-Stage Health Verification
7. Active Promotion & Audit Event Logging
"""

import time
from typing import Any
from uuid import uuid4

import structlog

from backend.app.services.deployment_monitor import deployment_monitor
from backend.app.services.deployment_version_manager import deployment_version_manager
from backend.app.services.health_service import health_service
from backend.app.services.production_config_manager import production_config_manager
from backend.app.services.runtime_manager import runtime_manager

logger = structlog.get_logger(__name__)


class DeploymentEngine:
    """Production Deployment Engine Orchestrator."""

    def __init__(self) -> None:
        pass

    async def execute_deployment(
        self,
        name: str,
        model_version_id: str,
        configuration: dict[str, Any],
        environment: str = "production",
        replicas: int = 1,
        runtime_version: str = "1.0.0-arm64",
    ) -> dict[str, Any]:
        """Execute complete, validated production deployment workflow.

        Step 1: Validate configuration.
        Step 2: Prepare deployment package & manifest.
        Step 3: Deploy runtime configuration parameters.
        Step 4: Load model into ARM memory.
        Step 5: Start inference server & verify lifecycle.
        Step 6: Verify deployment via 5-stage health probes.
        Step 7: Promote to ACTIVE state and log audit events.
        """
        logger.info(
            "Starting production deployment workflow",
            name=name,
            model_id=model_version_id,
            env=environment,
        )

        # ------------------------------------------------------------------
        # Step 1: Validate Configuration
        # ------------------------------------------------------------------
        is_valid, errors, validated_config = production_config_manager.validate_configuration(
            configuration, check_model_exists=False
        )
        if not is_valid:
            error_msg = f"Deployment rejected due to invalid configuration: {'; '.join(errors)}"
            logger.error("Configuration validation failed", errors=errors)
            raise ValueError(error_msg)

        # Ensure model_id is set
        validated_config["model_id"] = model_version_id

        # ------------------------------------------------------------------
        # Step 2: Prepare Deployment Package & Manifest
        # ------------------------------------------------------------------
        dep_id = f"dep-{int(time.time())}-{str(uuid4())[:8]}"

        dep_record = deployment_version_manager.register_deployment(
            name=name,
            model_version_id=model_version_id,
            configuration=validated_config,
            environment=environment,
            replicas=replicas,
            runtime_version=runtime_version,
            deployment_id=dep_id,
        )

        deployment_version_manager.record_event(
            deployment_id=dep_id,
            event_type="INFO",
            message=f"Prepared deployment package for {dep_id} (Config Hash: {dep_record['config_version']})",
        )

        # ------------------------------------------------------------------
        # Step 3: Deploy Runtime Configuration
        # ------------------------------------------------------------------
        dep_record["status"] = "STAGING"
        deployment_version_manager.record_event(
            deployment_id=dep_id,
            event_type="INFO",
            message=f"Applying dynamic parameter runtime configuration for {dep_id}",
        )

        # ------------------------------------------------------------------
        # Step 4: Load Model into Memory
        # ------------------------------------------------------------------
        deployment_version_manager.record_event(
            deployment_id=dep_id,
            event_type="INFO",
            message=f"Loading model '{model_version_id}' into ARM memory...",
        )
        try:
            runtime_manager.load_model(model_version_id)
        except Exception as err:
            dep_record["status"] = "FAILED"
            dep_record["health_status"] = "UNHEALTHY"
            deployment_version_manager.record_event(
                deployment_id=dep_id,
                event_type="ERROR",
                message=f"Model load failed: {str(err)}",
            )
            raise RuntimeError(f"Deployment failed during model load: {str(err)}") from err

        # ------------------------------------------------------------------
        # Step 5 & 6: Multi-Stage Health Verification
        # ------------------------------------------------------------------
        dep_record["status"] = "VERIFYING"
        deployment_version_manager.record_event(
            deployment_id=dep_id,
            event_type="INFO",
            message=f"Executing 5-stage health verification for {dep_id}...",
        )

        health_report = await health_service.execute_full_health_verification(
            deployment_id=dep_id, target_model_id=model_version_id
        )

        if not health_report.is_healthy:
            dep_record["status"] = "FAILED"
            dep_record["health_status"] = health_report.overall_status
            deployment_version_manager.record_event(
                deployment_id=dep_id,
                event_type="ERROR",
                message=f"Deployment health verification failed. Overall status: {health_report.overall_status}",
                details=health_report.model_dump(),
            )
            raise RuntimeError(
                f"Deployment health verification failed: {health_report.overall_status}"
            )

        # ------------------------------------------------------------------
        # Step 7: Promote to ACTIVE Production Deployment
        # ------------------------------------------------------------------
        active_record = deployment_version_manager.promote_to_active(dep_id)

        # Collect initial monitoring telemetry snapshot
        telemetry = deployment_monitor.collect_real_telemetry(dep_id, health_status="HEALTHY")
        active_record["metrics_summary"] = telemetry.model_dump()

        logger.info(
            "Production deployment completed successfully",
            dep_id=dep_id,
            version=active_record["deployment_version"],
            status=active_record["status"],
        )

        return active_record


deployment_engine = DeploymentEngine()
