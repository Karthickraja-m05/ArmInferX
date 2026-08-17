"""Integration tests for model API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_models(client: AsyncClient) -> None:
    """Test the /api/v1/models endpoint."""
    response = await client.get("/api/v1/models")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
