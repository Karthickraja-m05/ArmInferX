"""Integration tests for performix API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_performix_results(client: AsyncClient) -> None:
    """Test the /api/v1/performix/results endpoint."""
    response = await client.get("/api/v1/performix/results")
    assert response.status_code == 200
    data = response.json()
    assert "total_count" in data
    assert "results" in data


@pytest.mark.asyncio
async def test_performix_report(client: AsyncClient) -> None:
    """Test the /api/v1/performix/report endpoint."""
    response = await client.get("/api/v1/performix/report?format=json")
    assert response.status_code == 200
    # Should return JSON content
    assert "application/json" in response.headers["content-type"]
