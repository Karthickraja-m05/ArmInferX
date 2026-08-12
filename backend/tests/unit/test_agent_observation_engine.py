"""Unit tests for Agent Observation Engine."""

from pathlib import Path
import pytest

from backend.app.services.agent_observation_engine import AgentObservationEngine


def test_agent_observation_engine(tmp_path: Path):
    """Test capturing full state snapshot of system resources, repositories, and active runtime config."""
    observer = AgentObservationEngine(target_dir=tmp_path)

    snapshot = observer.capture_state_snapshot(
        active_model_id="qwen2.5-0.5b-instruct",
        top_ranked_config_id="cfg-top-1",
        latest_quality_score=94.5,
        latest_cost_per_1m_tokens=0.145,
    )

    assert snapshot.active_model_id == "qwen2.5-0.5b-instruct"
    assert snapshot.system_resources.cpu_count >= 1
    assert snapshot.runtime_configuration["model_path"] is not None
    assert snapshot.latest_quality_score == 94.5
    assert (tmp_path / f"{snapshot.snapshot_id}.json").exists()
