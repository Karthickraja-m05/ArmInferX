"""Unit tests for Agent Recommendation Engine."""

from pathlib import Path
import pytest

from backend.app.services.agent_decision_engine import ActionDecision
from backend.app.services.agent_observation_engine import AgentStateSnapshot, SystemResourceState
from backend.app.services.agent_planning_engine import OptimizationPlan
from backend.app.services.agent_recommendation_engine import AgentRecommendationEngine
from backend.app.services.agent_workflow_orchestrator import WorkflowExecutionRecord, WorkflowStepRecord


def test_agent_recommendation_engine(tmp_path: Path):
    """Test generating explainable recommendation reports from workflow records."""
    engine = AgentRecommendationEngine(target_dir=tmp_path)

    sys_res = SystemResourceState(
        cpu_count=4,
        cpu_percent=30.0,
        memory_total_mb=8000.0,
        memory_used_mb=2000.0,
        memory_percent=25.0,
    )
    snap = AgentStateSnapshot(
        snapshot_id="snap-test",
        timestamp="2026-08-12T00:00:00Z",
        active_model_id="qwen2.5-0.5b-instruct",
        runtime_configuration={"thread_count": 4, "batch_size": 64, "quantization_variant": "Q4_K_M"},
        system_resources=sys_res,
        total_experiments_recorded=2,
        total_benchmarks_recorded=2,
        total_quality_evaluations=2,
        total_cost_calculations=2,
        recent_experiment_ids=["exp-1", "exp-2"],
        recent_benchmark_ids=["bench-1", "bench-2"],
    )
    plan = OptimizationPlan(
        plan_id="plan-test",
        snapshot_id="snap-test",
        timestamp="2026-08-12T00:00:00Z",
        proposals=[],
        rationale="Test Plan",
    )
    dec1 = ActionDecision(
        decision_id="dec-1",
        snapshot_id="snap-test",
        timestamp="2026-08-12T00:00:00Z",
        action_type="EXECUTE_PLAN",
        chosen_proposal_id="p-1",
        target_configuration={"config_id": "cfg-1", "thread_count": 4, "batch_size": 64},
        reasoning="Exploration trial 1",
    )
    dec2 = ActionDecision(
        decision_id="dec-2",
        snapshot_id="snap-test",
        timestamp="2026-08-12T00:00:00Z",
        action_type="EXECUTE_PLAN",
        chosen_proposal_id="p-2",
        target_configuration={"config_id": "cfg-2", "thread_count": 8, "batch_size": 128},
        reasoning="Exploration trial 2",
    )

    s1 = WorkflowStepRecord(
        step_number=1,
        snapshot=snap,
        plan=plan,
        decision=dec1,
        experiment_id="exp-1",
        benchmark_id="bench-1",
        quality_score=90.0,
        cost_per_1m_tokens=0.025,
        composite_utility_score=85.0,
    )
    s2 = WorkflowStepRecord(
        step_number=2,
        snapshot=snap,
        plan=plan,
        decision=dec2,
        experiment_id="exp-2",
        benchmark_id="bench-2",
        quality_score=95.0,
        cost_per_1m_tokens=0.016,
        composite_utility_score=98.5,
    )

    wf = WorkflowExecutionRecord(
        workflow_id="wf-test-rec",
        target_model_id="qwen2.5-0.5b-instruct",
        timestamp="2026-08-12T00:00:00Z",
        status="COMPLETED",
        total_steps_executed=2,
        stopping_reason="Optimization target converged with utility >= 98.0.",
        best_config_id="cfg-2",
        best_utility_score=98.5,
        steps=[s1, s2],
    )

    report = engine.generate_recommendation(wf)

    assert report.recommendation_id.startswith("agrec-")
    assert report.selected_config_id == "cfg-2"
    assert report.composite_utility_score == 98.5
    assert len(report.rejected_alternatives) == 1
    assert report.rejected_alternatives[0].config_id == "cfg-1"
    assert report.quality_impact.passed_quality_sla is True
    assert report.cost_impact.cost_reduction_pct > 0
    assert "cfg-2" in report.human_readable_narrative
    assert (tmp_path / f"{report.recommendation_id}.json").exists()
    assert (tmp_path / "latest.json").exists()
