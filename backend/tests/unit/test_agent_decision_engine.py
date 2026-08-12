"""Unit tests for Agent Decision Engine."""

from pathlib import Path
import pytest

from backend.app.services.agent_decision_engine import AgentDecisionEngine
from backend.app.services.agent_observation_engine import AgentObservationEngine
from backend.app.services.agent_planning_engine import AgentPlanningEngine


def test_agent_decision_engine(tmp_path: Path):
    """Test action evaluation, stopping criteria (max steps, convergence), and decision persistence."""
    obs_engine = AgentObservationEngine(target_dir=tmp_path / "obs")
    snapshot = obs_engine.capture_state_snapshot()

    planner = AgentPlanningEngine(target_dir=tmp_path / "plans")
    plan = planner.create_plan(snapshot)

    dec_engine = AgentDecisionEngine(target_dir=tmp_path / "dec")

    # 1. Normal step -> EXECUTE_PLAN
    d1 = dec_engine.evaluate_decision(snapshot, plan, current_step=1, max_steps=5)
    assert d1.action == "EXECUTE_PLAN"
    assert d1.target_proposal_id is not None

    # 2. Max steps -> STOP_MAX_EXPERIMENTS
    d2 = dec_engine.evaluate_decision(snapshot, plan, current_step=6, max_steps=5)
    assert d2.action == "STOP_MAX_EXPERIMENTS"

    # 3. Score plateau -> STOP_CONVERGED
    d3 = dec_engine.evaluate_decision(
        snapshot,
        plan,
        current_step=2,
        max_steps=5,
        historical_scores=[80.0, 80.1, 80.2],  # delta = 0.2 < 0.5
    )
    assert d3.action == "STOP_CONVERGED"
