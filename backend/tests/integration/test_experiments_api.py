"""Integration test for experiments API."""

from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_list_experiment(client: AsyncClient) -> None:
    model_id = str(uuid4())
    payload = {
        "name": "integration-exp",
        "model_id": model_id,
        "constraints": {
            "max_latency_p99_ms": 12.5,
            "min_throughput_rps": 300.0,
        },
        "search_space": {
            "runtimes": ["onnxruntime"],
            "quantizations": ["int8"],
            "instance_types": ["c7g.xlarge"],
            "batch_sizes": [1, 2],
        },
        "budget": 5,
    }

    # Create
    res = await client.post("/api/v1/experiments", json=payload)
    assert res.status_code == 201
    exp_data = res.json()
    assert exp_data["name"] == "integration-exp"
    assert exp_data["status"] == "CREATED"

    exp_id = exp_data["id"]

    # List
    list_res = await client.get("/api/v1/experiments")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) >= 1

    # Fetch detail
    detail_res = await client.get(f"/api/v1/experiments/{exp_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == exp_id
