"""Integration tests for Autonomous Optimization Agent REST APIs."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app
from backend.app.services.agent_workflow_orchestrator import WorkflowExecutionRecord


@pytest.mark.asyncio
async def test_agent_api_endpoints(tmp_path: Path):
    """Test full agent API lifecycle: /agent/status, /agent/start, /agent/stop, /agent/history, /agent/recommendation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /agent/status
        res_status = await client.get("/agent/status")
        assert res_status.status_code == 200
        st = res_status.json()
        assert "status" in st
        assert "is_running" in st

        # 2. GET /api/v1/agent/status (Prefix test)
        res_v1_status = await client.get("/api/v1/agent/status")
        assert res_v1_status.status_code == 200

        # 3. GET /agent/history (Initial empty / list)
        res_hist = await client.get("/agent/history?limit=5&offset=0")
        assert res_hist.status_code == 200
        h_data = res_hist.json()
        assert "total_count" in h_data
        assert "workflows" in h_data

        # 4. POST /agent/stop when idle
        res_stop = await client.post("/agent/stop")
        assert res_stop.status_code == 200
        assert res_stop.json()["status"] == "NOT_RUNNING"

        # 5. Mock workflow execution for POST /agent/start
        mock_wf = WorkflowExecutionRecord(
            workflow_id="wf-mock-api-test",
            target_model_id="qwen2.5-0.5b-instruct",
            timestamp="2026-08-12T00:00:00Z",
            status="COMPLETED",
            total_steps_executed=2,
            stopping_reason="Optimization target converged.",
            best_config_id="cfg-api-1",
            best_utility_score=98.8,
            steps=[],
        )

        with patch("backend.app.api.v1.agent.agent_orchestrator.run_autonomous_optimization_loop", AsyncMock(return_value=mock_wf)):
            res_start = await client.post(
                "/agent/start",
                json={
                    "target_model_id": "qwen2.5-0.5b-instruct",
                    "max_steps": 2,
                    "background": False,
                },
            )
            assert res_start.status_code == 200
            start_data = res_start.json()
            assert start_data["status"] == "COMPLETED"
            assert start_data["workflow_id"] == "wf-mock-api-test"
            assert start_data["workflow_record"] is not None

        # 6. GET /agent/recommendation
        res_rec = await client.get("/agent/recommendation")
        assert res_rec.status_code == 200
        rec_json = res_rec.json()
        assert "recommendation_id" in rec_json
        assert "composite_utility_score" in rec_json
        assert "performance_improvements" in rec_json
        assert "quality_impact" in rec_json
        assert "cost_impact" in rec_json
        assert "human_readable_narrative" in rec_json
