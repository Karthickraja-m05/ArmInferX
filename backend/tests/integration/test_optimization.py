"""Integration tests for optimization API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_optimization_rankings(client: AsyncClient) -> None:
    """Test the /api/v1/optimization/rankings endpoint."""
    response = await client.get("/api/v1/optimization/rankings")
    assert response.status_code == 200
    data = response.json()
    assert "top_configurations" in data


@pytest.mark.asyncio
async def test_optimization_recommendations(client: AsyncClient) -> None:
    """Test the /api/v1/optimization/recommendations endpoint."""
    response = await client.get("/api/v1/optimization/recommendations")
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
