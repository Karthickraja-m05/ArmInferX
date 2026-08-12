"""Unit tests for Agent Planning Engine."""

from pathlib import Path
import pytest

from backend.app.services.agent_observation_engine import AgentObservationEngine
from backend.app.services.agent_planning_engine import AgentPlanningEngine


def test_agent_planning_engine(tmp_path: Path):
    """Test experiment proposal generation, deduplication, and hypothesis formulation."""
    obs_engine = AgentObservationEngine(target_dir=tmp_path / "obs")
    snapshot = obs_engine.capture_state_snapshot()

    planner = AgentPlanningEngine(target_dir=tmp_path / "plans")
    plan = planner.create_plan(snapshot, target_model_id="qwen2.5-0.5b-instruct")

    assert plan.snapshot_id == snapshot.snapshot_id
    assert len(plan.proposals) >= 1
    prop = plan.proposals[0]
    assert prop.expected_improvement_hypothesis is not None
    assert prop.hash_signature is not None

    # Test deduplication on second run
    plan2 = planner.create_plan(snapshot, target_model_id="qwen2.5-0.5b-instruct")
    hashes_1 = [p.hash_signature for p in plan.proposals]
    hashes_2 = [p.hash_signature for p in plan2.proposals]
    assert set(hashes_1).isdisjoint(set(hashes_2)) or plan2.proposals[0].objective == "Fallback Exploration Trial"
