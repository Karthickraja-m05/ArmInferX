"""Integration tests for experiment API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_experiments(client: AsyncClient) -> None:
    """Test the /api/v1/experiments endpoint."""
    response = await client.get("/api/v1/experiments")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
