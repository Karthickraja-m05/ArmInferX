"""Integration tests for backend foundation system endpoints and structured error handling."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_health_endpoint(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "environment" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_root_readiness_endpoint(client: AsyncClient) -> None:
    response = await client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"
    assert "latency_ms" in data


@pytest.mark.asyncio
async def test_system_info_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/system/info")
    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == "ArmServe API"
    assert data["version"] == "0.1.0"
    assert data["api_version"] == "v1"
    assert "python_version" in data
    assert "platform" in data
    assert "architecture" in data
    assert "database_dialect" in data
    assert isinstance(data["runtimes_supported"], list)
    assert "onnxruntime" in data["runtimes_supported"]

    # Verify secret safety (no sensitive keys exposed in body)
    text = response.text.lower()
    assert "secret" not in text
    assert "password" not in text
    assert "access_key" not in text


@pytest.mark.asyncio
async def test_system_health_v1_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/system/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_openapi_docs_and_schema_endpoint(client: AsyncClient) -> None:
    docs_res = await client.get("/docs")
    assert docs_res.status_code == 200

    openapi_res = await client.get("/api/v1/openapi.json")
    assert openapi_res.status_code == 200
    data = openapi_res.json()
    assert data["info"]["title"] == "ArmServe API"


@pytest.mark.asyncio
async def test_structured_not_found_error(client: AsyncClient) -> None:
    response = await client.get("/api/v1/non_existent_route")
    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "NOT_FOUND"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_structured_validation_error(client: AsyncClient) -> None:
    response = await client.post("/api/v1/models", json={})
    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "VALIDATION_ERROR"
    assert data["message"] == "Request validation failed"
    assert isinstance(data["details"], list)
