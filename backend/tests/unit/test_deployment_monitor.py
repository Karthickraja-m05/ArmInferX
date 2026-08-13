"""Unit tests for Deployment Monitoring."""

import pytest
from backend.app.services.deployment_monitor import deployment_monitor


def test_collect_real_telemetry():
    """Test gathering real telemetry measurements and alert generation."""
    telemetry = deployment_monitor.collect_real_telemetry(
        deployment_id="dep-mon-test", health_status="HEALTHY"
    )

    assert telemetry.deployment_id == "dep-mon-test"
    assert telemetry.request_count >= 0
    assert telemetry.requests_per_second >= 0.0
    assert telemetry.tokens_per_second >= 0.0
    assert telemetry.cpu_percent >= 0.0
    assert telemetry.memory_mb >= 0.0
    assert telemetry.availability_percent >= 0.0

    history = deployment_monitor.get_monitoring_history("dep-mon-test")
    assert len(history) >= 1
