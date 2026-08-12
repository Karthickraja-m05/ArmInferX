"""Unit tests for ArmServe observability, metrics collection, and credential masking."""

from fastapi.testclient import TestClient

from backend.app.core.logging import mask_sensitive_data
from backend.app.core.metrics import MetricsCollector
from backend.app.main import app


def test_mask_sensitive_data_redacts_credentials() -> None:
    """Verify structlog processor masks passwords, tokens, API keys, and secret credentials."""
    log_event = {
        "event": "User login attempt",
        "username": "alice",
        "password": "SuperSecretPassword123!",
        "api_key": "arm_live_998877665544332211",
        "nested_config": {
            "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "log_level": "INFO",
        },
    }

    masked = mask_sensitive_data(None, "info", log_event)

    assert masked["username"] == "alice"
    assert masked["password"] == "********"
    assert masked["api_key"] == "********"
    assert masked["nested_config"]["aws_secret_access_key"] == "********"
    assert masked["nested_config"]["log_level"] == "INFO"


def test_metrics_collector_record_request() -> None:
    """Verify recording HTTP requests updates counters and latency histograms."""
    collector = MetricsCollector()
    collector.record_request("GET", "/api/v1/models/123", 200, 0.045)

    summary = collector.get_summary()
    assert summary["total_requests"] == 1
    assert "GET /api/v1/models/{id} 200" in summary["requests_by_status"]

    prom_text = collector.generate_prometheus_text()
    assert (
        'http_requests_total{method="GET",endpoint="/api/v1/models/{id}",status="200"} 1'
        in prom_text
    )
    assert (
        'http_request_duration_seconds_count{method="GET",endpoint="/api/v1/models/{id}"} 1'
        in prom_text
    )


def test_metrics_collector_record_errors() -> None:
    """Verify recording application errors updates error counters."""
    collector = MetricsCollector()
    collector.record_error("ValueError", 400, "/api/v1/experiments")

    summary = collector.get_summary()
    assert summary["total_errors"] == 1
    assert "ValueError (400) /api/v1/experiments" in summary["errors_by_type"]

    prom_text = collector.generate_prometheus_text()
    assert (
        'http_errors_total{error_type="ValueError",status="400",endpoint="/api/v1/experiments"} 1'
        in prom_text
    )


def test_metrics_collector_record_db_operation() -> None:
    """Verify database operation metrics tracking."""
    collector = MetricsCollector()
    collector.record_db_operation("select", "success", 0.012)
    collector.record_db_operation("insert", "error", 0.035)

    summary = collector.get_summary()
    assert summary["total_db_operations"] == 2
    assert summary["db_operations"]["select (success)"] == 1
    assert summary["db_operations"]["insert (error)"] == 1

    prom_text = collector.generate_prometheus_text()
    assert 'db_operations_total{operation="select",status="success"} 1' in prom_text
    assert 'db_operations_total{operation="insert",status="error"} 1' in prom_text


def test_prometheus_metrics_endpoints() -> None:
    """Verify /metrics and /api/v1/system/metrics return valid Prometheus text format."""
    client = TestClient(app)

    res1 = client.get("/metrics")
    assert res1.status_code == 200
    assert "text/plain" in res1.headers["content-type"]
    assert "armserve_app_info" in res1.text
    assert "http_requests_total" in res1.text

    res2 = client.get("/api/v1/system/metrics")
    assert res2.status_code == 200
    assert "text/plain" in res2.headers["content-type"]
    assert "http_requests_total" in res2.text
