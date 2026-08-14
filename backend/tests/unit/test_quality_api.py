"""Unit tests for Quality REST API endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.quality_scoring_engine import QualityEvaluationReport

client = TestClient(app)


def test_quality_api_results():
    """Test GET /api/v1/quality/results listing endpoint."""
    res = client.get("/api/v1/quality/results")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "items" in data


@pytest.mark.asyncio
async def test_quality_api_run():
    """Test POST /api/v1/quality/run endpoint."""
    mock_eval = QualityEvaluationReport(
        evaluation_id="eval-api-test",
        collection_id="coll-api",
        config_id="cfg-002d5491f3",
        experiment_id="exp-1786554838",
        timestamp="2026-08-12T00:00:00Z",
        overall_quality_score=94.0,
        passed=True,
        category_scores={"reasoning": 94.0},
        dimension_scores={"correctness": 95.0, "completeness": 93.0},
        prompt_scores=[],
    )

    with patch(
        "backend.app.api.v1.quality.scoring_engine.evaluate_collection_record",
        return_value=mock_eval,
    ):
        res = client.post(
            "/api/v1/quality/run",
            json={"config_id": "cfg-002d5491f3", "dataset_id": "eval-core-v1"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["evaluation"]["evaluation_id"] == "eval-api-test"
        assert "markdown_report" in data
