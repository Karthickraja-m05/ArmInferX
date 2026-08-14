"""Unit tests for Telemetry Metrics Collector and Benchmark Comparison Engine."""

from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.benchmark_comparator import BenchmarkComparator
from backend.app.services.metrics_collector import MetricsCollector

client = TestClient(app)


def test_metrics_collector_system_metrics():
    """Test live system metrics capture."""
    sys_metrics = MetricsCollector.capture_system_metrics()
    assert sys_metrics.cpu_utilization_percent >= 0.0
    assert sys_metrics.memory_used_mb > 0.0
    assert sys_metrics.disk_used_gb > 0.0


def test_metrics_collector_full_snapshot():
    """Test full telemetry metrics snapshot construction."""
    snap = MetricsCollector.capture_full_snapshot(
        run_id="test-run-123",
        latency_ms=25.0,
        ttft_ms=5.0,
        prompt_tokens=20,
        completion_tokens=50,
    )
    assert snap.run_id == "test-run-123"
    assert snap.inference.total_latency_ms == 25.0
    assert snap.inference.time_to_first_token_ms == 5.0
    assert snap.inference.tokens_per_second > 0.0
    assert snap.runtime.context_size > 0


def test_benchmark_comparator_evaluation():
    """Test comparison logic and regression detection."""
    run_a = {
        "run_id": "bench-run-a",
        "timestamp": "2026-08-12T20:00:00Z",
        "latency_p50_ms": 10.0,
        "latency_p90_ms": 15.0,
        "latency_p99_ms": 20.0,
        "requests_per_second": 100.0,
        "tokens_per_second": 2000.0,
        "peak_memory_mb": 400.0,
    }

    run_b = {
        "run_id": "bench-run-b",
        "timestamp": "2026-08-12T21:00:00Z",
        "latency_p50_ms": 8.0,  # Improved
        "latency_p90_ms": 12.0,  # Improved
        "latency_p99_ms": 16.0,  # Improved
        "requests_per_second": 120.0,  # Improved
        "tokens_per_second": 2400.0,  # Improved
        "peak_memory_mb": 390.0,  # Improved
    }

    with patch.object(BenchmarkComparator, "load_run_manifest", side_effect=[run_a, run_b]):
        report = BenchmarkComparator.compare_runs("bench-run-a", "bench-run-b")
        assert report.run_a_id == "bench-run-a"
        assert report.run_b_id == "bench-run-b"
        assert report.verdict == "IMPROVED"
        assert len(report.comparisons) == 6


@pytest.mark.asyncio
async def test_compare_benchmarks_api_endpoint():
    """Test POST /api/v1/benchmarks/compare REST API endpoint."""
    run_a = {
        "run_id": "bench-1",
        "timestamp": "2026-08-12T20:00:00Z",
        "latency_p50_ms": 10.0,
        "latency_p90_ms": 15.0,
        "latency_p99_ms": 20.0,
        "requests_per_second": 100.0,
        "tokens_per_second": 2000.0,
        "peak_memory_mb": 400.0,
    }
    run_b = {
        "run_id": "bench-2",
        "timestamp": "2026-08-12T21:00:00Z",
        "latency_p50_ms": 15.0,  # Regressed (+50%)
        "latency_p90_ms": 20.0,
        "latency_p99_ms": 25.0,
        "requests_per_second": 80.0,
        "tokens_per_second": 1600.0,
        "peak_memory_mb": 410.0,
    }

    with patch.object(BenchmarkComparator, "load_run_manifest", side_effect=[run_a, run_b]):
        res = client.post("/api/v1/benchmarks/compare?run_a_id=bench-1&run_b_id=bench-2")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["verdict"] == "REGRESSED"
        assert any(c["is_regression"] for c in data["comparisons"])
