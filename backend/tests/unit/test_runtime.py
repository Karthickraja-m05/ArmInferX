"""Unit tests for ArmServe Backend Runtime Integration & Model Lifecycle Manager."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.runtime_manager import runtime_manager, ModelLifecycleState

client = TestClient(app)


def test_get_runtime_status_endpoint():
    """Test GET /runtime/status endpoint."""
    response = client.get("/runtime/status")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["engine"] == "ArmServe-GGUF-MLAS"
    assert data["architecture"] == "aarch64"


def test_discover_models_endpoint():
    """Test GET /models endpoint."""
    response = client.get("/models")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "data" in data
    model_ids = [m["id"] for m in data["data"]]
    assert "qwen2.5-0.5b-instruct" in model_ids


def test_direct_inference_endpoint():
    """Test POST /inference endpoint."""
    payload = {
        "prompt": "Test inference integration payload",
        "model": "qwen2.5-0.5b-instruct",
        "max_tokens": 50,
    }
    response = client.post("/inference", json=payload)
    assert response.status_code == status.HTTP_200_OK
    res = response.json()
    assert res["object"] == "chat.completion"
    assert len(res["choices"]) > 0


def test_model_lifecycle_unload_and_load():
    """Test model unload, query status, and load lifecycle."""
    model_id = "qwen2.5-0.5b-instruct"

    # Unload
    res_unload = client.post(f"/api/v1/models/{model_id}/unload")
    assert res_unload.status_code == status.HTTP_200_OK
    assert res_unload.json()["status"] == ModelLifecycleState.UNLOADED.value

    # Query Status
    res_status = client.get(f"/api/v1/models/{model_id}/status")
    assert res_status.status_code == status.HTTP_200_OK
    assert res_status.json()["status"] == ModelLifecycleState.UNLOADED.value
    assert not res_status.json()["is_active"]

    # Load
    res_load = client.post(f"/api/v1/models/{model_id}/load")
    assert res_load.status_code == status.HTTP_200_OK
    assert res_load.json()["status"] == ModelLifecycleState.LOADED.value
    assert res_load.json()["is_active"]
