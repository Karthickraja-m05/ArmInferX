"""Unit tests for Experiment Executor and Experiments API Router."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.experiment_executor import ExperimentExecutor
from backend.app.services.experiment_generator import ConfigurationGenerator, ParameterRangeSpec

client = TestClient(app)


def test_list_experiments_endpoint():
    """Test GET /api/v1/experiments endpoint."""
    res = client.get("/api/v1/experiments")
    assert res.status_code == status.HTTP_200_OK
    assert isinstance(res.json(), list)


def test_generate_experiment_configs_endpoint(tmp_path: Path):
    """Test POST /api/v1/experiments/generate endpoint with isolated test directory."""
    payload = {
        "thread_counts": [1, 2],
        "batch_sizes": [64],
        "context_lengths": [2048],
        "temperatures": [0.0],
        "max_tokens_list": [128],
        "model_id": "qwen2.5-0.5b-instruct",
    }
    with patch("backend.app.api.v1.experiments.ConfigurationGenerator") as mock_gen_cls:
        instance = ConfigurationGenerator(target_dir=tmp_path)
        mock_gen_cls.return_value = instance
        res = client.post("/api/v1/experiments/generate", json=payload)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert len(data) == 2
        assert data[0]["config_id"].startswith("cfg-")


@pytest.mark.asyncio
async def test_experiment_executor_pipeline(tmp_path: Path):
    """Test full experiment execution pipeline with isolated directory."""
    generator = ConfigurationGenerator(target_dir=tmp_path)
    spec = ParameterRangeSpec(
        thread_counts=[2],
        batch_sizes=[128],
        context_lengths=[2048],
        temperatures=[0.7],
        max_tokens_list=[256],
    )
    configs = generator.generate_configurations(spec)
    assert len(configs) >= 1
    target_cfg = configs[0]

    executor = ExperimentExecutor()

    # Patch load_config to return our isolated config
    with patch.object(ExperimentExecutor, "load_config", return_value=target_cfg):
        exp_run = await executor.execute_experiment(target_cfg.config_id, warmup_iterations=1, benchmark_iterations=2)
        assert exp_run.status == "COMPLETED"
        assert exp_run.benchmark_run_id is not None
        assert exp_run.metrics_summary["requests_per_second"] > 0
