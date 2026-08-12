"""Integration test for real database health check functions."""

import pytest
from httpx import AsyncClient

from backend.app.core.database import check_database_health


@pytest.mark.asyncio
async def test_database_health_check_function() -> None:
    health = await check_database_health()
    assert health["status"] == "healthy"
    assert "latency_ms" in health
    assert health["latency_ms"] >= 0
    assert "database_dialect" in health


@pytest.mark.asyncio
async def test_health_api_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/system/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
