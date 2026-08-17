"""Integration tests for deployment API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_deployments(client: AsyncClient) -> None:
    """Test the /api/v1/deployments endpoint."""
    response = await client.get("/api/v1/deployments")
    assert response.status_code == 200
    data = response.json()
    assert "total_count" in data
    assert "deployments" in data


@pytest.mark.asyncio
async def test_get_deployments_health(client: AsyncClient) -> None:
    """Test the /api/v1/deployments/health endpoint."""
    response = await client.get("/api/v1/deployments/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
