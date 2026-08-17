"""Integration tests for Deployment REST APIs and System Probes."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app


@pytest.mark.asyncio
async def test_probes_endpoints():
    """Test standard Kubernetes / cloud probes: /health, /ready, /live."""
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_health = await client.get("/health")
        assert res_health.status_code == 200
        assert res_health.json()["status"] in ["healthy", "degraded"]

        res_ready = await client.get("/ready")
        assert res_ready.status_code in [200, 530, 533]
        assert "status" in res_ready.json()


@pytest.mark.asyncio
async def test_deployments_crud_workflow():
    """Test full deployment lifecycle: creation, listing, active retrieval, history, comparison, rollback."""
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. POST /deployments (Create deployment)
        payload = {
            "name": "prod-release-v1",
            "model_version_id": "qwen2.5-0.5b-instruct",
            "configuration": {
                "model_id": "qwen2.5-0.5b-instruct",
                "thread_count": 4,
                "batch_size": 32,
                "context_length": 2048,
                "temperature": 0.7,
                "max_tokens": 256,
            },
            "environment": "production",
            "replicas": 1,
            "runtime_version": "1.0.0-arm64",
        }

        res_create = await client.post("/deployments", json=payload)
        assert res_create.status_code == 201
        dep_data = res_create.json()
        dep_id = dep_data["id"]
        assert dep_data["name"] == "prod-release-v1"
        assert dep_data["is_active"] is True
        assert dep_data["status"] == "ACTIVE"

        # 2. GET /deployments (List history)
        res_list = await client.get("/deployments?limit=10")
        assert res_list.status_code == 200
        assert res_list.json()["total_count"] >= 1

        # 3. GET /deployments/active (Active deployment)
        res_act = await client.get("/deployments/active")
        assert res_act.status_code == 200
        assert res_act.json()["id"] == dep_id

        # 4. GET /deployments/{id} (Details & events)
        res_det = await client.get(f"/deployments/{dep_id}")
        assert res_det.status_code == 200
        det_json = res_det.json()
        assert det_json["deployment"]["id"] == dep_id
        assert len(det_json["events"]) >= 1

        # 5. GET /deployments/{id}/monitoring
        res_mon = await client.get(f"/deployments/{dep_id}/monitoring")
        assert res_mon.status_code == 200
        mon_json = res_mon.json()
        assert mon_json["deployment_id"] == dep_id
        assert "requests_per_second" in mon_json

        # 6. POST /deployments/config/compare
        res_cmp = await client.post(
            "/deployments/config/compare",
            json={
                "config1": {"thread_count": 4, "batch_size": 16},
                "config2": {"thread_count": 8, "batch_size": 16},
            },
        )
        assert res_cmp.status_code == 200
        cmp_json = res_cmp.json()
        assert cmp_json["match"] is False
        assert len(cmp_json["differences"]) == 1

        # 7. POST /deployments (Create second deployment to enable rollback test)
        from typing import Any

        payload2: dict[str, Any] = dict(payload)
        payload2["name"] = "prod-release-v2"
        payload2["configuration"]["thread_count"] = 8
        res_create2 = await client.post("/deployments", json=payload2)
        assert res_create2.status_code == 201
        dep_id2 = res_create2.json()["id"]

        # 8. POST /deployments/{id}/rollback
        res_rb = await client.post(
            f"/deployments/{dep_id2}/rollback",
            json={"reason": "High latency detected in release v2"},
        )
        assert res_rb.status_code == 200
        rb_json = res_rb.json()
        assert rb_json["success"] is True
        assert rb_json["rolled_back_deployment_id"] == dep_id2
        assert rb_json.get("restored_deployment_id") is not None
