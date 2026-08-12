"""Unit tests for ArmServe Benchmark Runner and Benchmark API Router."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from backend.app.main import app
from cli.main import app as cli_app

client = TestClient(app)
runner = CliRunner()


def test_list_benchmarks_endpoint():
    """Test GET /api/v1/benchmarks endpoint."""
    response = client.get("/api/v1/benchmarks")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_benchmark_run_endpoint():
    """Test POST /api/v1/benchmarks/run endpoint."""
    payload = {
        "model_id": "qwen2.5-0.5b-instruct",
        "warmup_iterations": 1,
        "iterations": 2,
        "concurrency": 1,
        "prompt": "Test benchmark prompt",
    }
    response = client.post("/api/v1/benchmarks/run", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "run_id" in data
    assert data["total_requests"] == 2
    assert data["successful_requests"] == 2
    assert data["requests_per_second"] > 0
    assert data["tokens_per_second"] > 0
    assert data["latency_p50_ms"] > 0


def test_cli_benchmark_run_command():
    """Test CLI armserve benchmark run command with mocked HTTP response."""
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "run_id": "bench-test-1234",
        "timestamp": "2026-08-12T22:00:00Z",
        "total_requests": 2,
        "successful_requests": 2,
        "duration_seconds": 0.05,
        "requests_per_second": 40.0,
        "tokens_per_second": 500.0,
        "latency_p50_ms": 10.0,
        "latency_p90_ms": 12.0,
        "latency_p99_ms": 15.0,
        "peak_memory_mb": 400.0,
    }

    mock_client = MagicMock()
    mock_client.post.return_value = mock_res
    mock_client.__enter__.return_value = mock_client

    with patch("cli.commands.benchmark.httpx.Client", return_value=mock_client):
        res = runner.invoke(cli_app, ["benchmark", "run", "--json", "-i", "2", "-w", "1"])
        assert res.exit_code == 0
        assert "bench-test-1234" in res.output
        assert "Throughput" in res.output or "total_requests" in res.output
