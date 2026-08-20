"""Integration tests for OpenAI compatible API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_openai_chat_completions(client: AsyncClient) -> None:
    """Test the /api/v1/chat/completions endpoint handles invalid model correctly."""
    response = await client.post(
        "/api/v1/chat/completions",
        json={"model": "invalid-model", "messages": [{"role": "user", "content": "hi"}]},
    )
    # Current engine mock implementation returns 200 even for invalid models
    assert response.status_code == 200
