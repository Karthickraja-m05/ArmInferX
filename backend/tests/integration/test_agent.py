"""Integration tests for autonomous agent API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_agent_status_endpoint(client: AsyncClient) -> None:
    """Test the /api/v1/agent/status endpoint."""
    response = await client.get("/api/v1/agent/status")
    assert response.status_code == 200
    data = response.json()
    assert "is_running" in data
    assert "state" in data


@pytest.mark.asyncio
async def test_agent_decisions_endpoint(client: AsyncClient) -> None:
    """Test the /api/v1/agent/decisions endpoint."""
    response = await client.get("/api/v1/agent/decisions")
    assert response.status_code == 200
    data = response.json()
    assert "decisions" in data


@pytest.mark.asyncio
async def test_agent_history_endpoint(client: AsyncClient) -> None:
    """Test the /api/v1/agent/history endpoint."""
    response = await client.get("/api/v1/agent/history")
    assert response.status_code == 200
    data = response.json()
    assert "workflows" in data
