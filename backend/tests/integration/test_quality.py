"""Integration tests for quality API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_quality_datasets(client: AsyncClient) -> None:
    """Test the /api/v1/quality/datasets endpoint."""
    response = await client.get("/api/v1/quality/datasets")
    assert response.status_code == 200
    data = response.json()
    assert "datasets" in data


@pytest.mark.asyncio
async def test_quality_evaluations(client: AsyncClient) -> None:
    """Test the /api/v1/quality/evaluations endpoint."""
    response = await client.get("/api/v1/quality/evaluations")
    assert response.status_code == 200
    data = response.json()
    assert "evaluations" in data
