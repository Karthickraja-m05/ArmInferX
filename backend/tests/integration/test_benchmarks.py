"""Integration tests for benchmark API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_benchmark_runs_endpoint(client: AsyncClient) -> None:
    """Test the /api/v1/benchmarks/runs endpoint."""
    response = await client.get("/api/v1/benchmarks/runs")
    assert response.status_code == 200
    data = response.json()
    assert "runs" in data
