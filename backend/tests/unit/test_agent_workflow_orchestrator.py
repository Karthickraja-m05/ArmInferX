"""Unit tests for Autonomous Workflow Orchestrator."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.services.agent_workflow_orchestrator import AgentWorkflowOrchestrator
from backend.app.services.quality_response_collector import EvaluationCollectionRecord
from backend.app.services.quality_scoring_engine import QualityEvaluationReport


@pytest.mark.asyncio
async def test_agent_workflow_orchestrator(tmp_path: Path):
    """Test full closed-loop autonomous optimization workflow execution."""
    orchestrator = AgentWorkflowOrchestrator(target_dir=tmp_path)
    orchestrator.observer.target_dir = tmp_path / "obs"
    orchestrator.planner.target_dir = tmp_path / "plans"
    orchestrator.planner.hashes_dir = tmp_path / "plans" / ".hashes"
    orchestrator.planner.hashes_dir.mkdir(parents=True, exist_ok=True)
    orchestrator.decision_engine.target_dir = tmp_path / "dec"

    mock_exp_res = {
        "experiment_id": "exp-mock-wf",
        "status": "COMPLETED",
        "benchmark_result": {
            "benchmark_id": "bench-mock-wf",
            "metrics_summary": {
                "total_duration_sec": 2.0,
                "requests_per_second": 100.0,
                "tokens_per_second": 2500.0,
                "cpu_utilization_pct": 45.0,
                "peak_memory_mb": 400.0,
                "average_memory_mb": 350.0,
                "latency_p50_ms": 5.0,
                "latency_p99_ms": 6.0,
            },
        },
    }

    mock_q_coll = EvaluationCollectionRecord(
        collection_id="coll-mock-wf",
        dataset_id="eval-core-v1",
        config_id="cfg-1",
        experiment_id="exp-mock-wf",
        timestamp="2026-08-12T00:00:00Z",
        responses=[],
    )

    mock_q_report = QualityEvaluationReport(
        evaluation_id="eval-wf-test",
        collection_id="coll-mock-wf",
        config_id="cfg-1",
        experiment_id="exp-mock-wf",
        timestamp="2026-08-12T00:00:00Z",
        overall_quality_score=90.0,
        passed=True,
        category_scores={"reasoning": 90.0},
        dimension_scores={"correctness": 90.0},
        prompt_scores=[],
    )

    with patch.object(orchestrator.executor, "execute_experiment", AsyncMock(return_value=mock_exp_res)), \
         patch.object(orchestrator.quality_collector, "collect_dataset_responses", AsyncMock(return_value=mock_q_coll)), \
         patch.object(orchestrator.quality_scorer, "evaluate_collection_record", return_value=mock_q_report):
        record = await orchestrator.run_autonomous_optimization_loop(
            target_model_id="qwen2.5-0.5b-instruct",
            max_steps=2,
        )

        assert record.status == "COMPLETED"
        assert record.total_steps_executed >= 1
        assert len(record.steps) >= 1
        assert record.steps[0].composite_utility_score is not None
