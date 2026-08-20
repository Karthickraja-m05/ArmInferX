"""Integration tests for runtime API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_runtime_status(client: AsyncClient) -> None:
    """Test the /api/v1/runtime/status endpoint."""
    response = await client.get("/api/v1/runtime/status")
    assert response.status_code == 200
    assert "status" in response.json()


@pytest.mark.asyncio
async def test_execute_inference(client: AsyncClient) -> None:
    """Test the /api/v1/inference endpoint."""
    response = await client.post(
        "/api/v1/inference", json={"prompt": "hello", "model": "test-model", "max_tokens": 100}
    )
    assert response.status_code == 200
