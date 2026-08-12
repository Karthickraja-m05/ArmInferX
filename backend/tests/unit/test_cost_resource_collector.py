"""Unit tests for Cost Resource Collector Engine."""

from pathlib import Path
import pytest

from backend.app.services.cost_resource_collector import CostResourceCollector


def test_cost_resource_collector(tmp_path: Path):
    """Test recording and retrieving actual resource measurements."""
    collector = CostResourceCollector(target_dir=tmp_path)

    m = collector.record_resource_usage(
        benchmark_id="bench-1",
        experiment_id="exp-1",
        config_id="cfg-1",
        cpu_utilization_pct=45.5,
        peak_memory_mb=350.0,
        average_memory_mb=320.0,
        execution_duration_sec=10.0,
        total_requests_processed=500,
        total_tokens_generated=10000,
        concurrency_level=4,
    )

    assert m.requests_per_second == 50.0
    assert m.tokens_per_second == 1000.0
    assert m.concurrency_level == 4

    retrieved = collector.get_measurement(m.measurement_id)
    assert retrieved is not None
    assert retrieved.config_id == "cfg-1"
