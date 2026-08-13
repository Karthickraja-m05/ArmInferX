"""Unit tests for Service Health Management."""

import pytest
from backend.app.services.health_service import health_service


@pytest.mark.asyncio
async def test_full_health_verification():
    """Test running 5-stage health verification."""
    report = await health_service.execute_full_health_verification(
        deployment_id="dep-unit-test", target_model_id="qwen2.5-0.5b-instruct"
    )

    assert report.deployment_id == "dep-unit-test"
    assert report.overall_status in ["HEALTHY", "DEGRADED", "UNHEALTHY"]
    assert report.startup_check.stage == "startup"
    assert report.model_check.stage == "model_loading"
    assert report.inference_check.stage == "inference"
    assert report.endpoint_check.stage == "endpoint"
    assert report.resource_check.stage == "resource"
    assert report.total_duration_ms > 0
