"""Unit tests for Configuration Ranker Engine."""

from pathlib import Path
import pytest

from backend.app.services.configuration_ranker import ConfigurationRanker
from backend.app.services.constraint_engine import ConstraintSpec


def test_configuration_ranker(tmp_path: Path):
    """Test ranking configurations by compliance, score, memory, and thread count."""
    ranker = ConfigurationRanker(target_dir=tmp_path)

    runs = [
        {
            "experiment_id": "exp-1",
            "config_id": "cfg-1",
            "configuration": {"thread_count": 4},
            "metrics_summary": {
                "latency_p50_ms": 4.0,
                "requests_per_second": 250.0,
                "peak_memory_mb": 400.0,
            },
        },
        {
            "experiment_id": "exp-2",
            "config_id": "cfg-2",
            "configuration": {"thread_count": 2},
            "metrics_summary": {
                "latency_p50_ms": 20.0,  # Fails SLA max 10ms
                "requests_per_second": 50.0,
                "peak_memory_mb": 800.0,
            },
        },
    ]

    spec = ConstraintSpec(max_latency_p50_ms=10.0)
    report = ranker.rank_experiment_runs(runs, constraint_spec=spec)

    assert report.total_evaluated == 2
    assert report.compliant_count == 1
    assert report.rejected_count == 1

    top1 = report.top_configurations[0]
    assert top1.rank == 1
    assert top1.config_id == "cfg-1"
    assert top1.is_compliant is True
