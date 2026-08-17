"""Integration tests for operational API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_system_info(client: AsyncClient) -> None:
    """Test the /api/v1/system/info endpoint."""
    response = await client.get("/api/v1/system/info")
    assert response.status_code == 200
    data = response.json()
    assert "app_name" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_system_config_validate(client: AsyncClient) -> None:
    """Test the /api/v1/system/config/validate endpoint."""
    response = await client.get("/api/v1/system/config/validate")
    assert response.status_code == 200
    data = response.json()
    assert "valid" in data
