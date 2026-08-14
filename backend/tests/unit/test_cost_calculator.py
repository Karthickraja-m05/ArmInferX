"""Unit tests for Cost Calculation Engine."""

from pathlib import Path

from backend.app.services.cost_calculator import CostCalculator, ProviderPricingConfig
from backend.app.services.cost_resource_collector import ResourceUsageMeasurement


def test_cost_calculator(tmp_path: Path) -> None:
    """Test cost calculation from measured resource usage using configurable AWS pricing."""
    calculator = CostCalculator(target_dir=tmp_path)

    measurement = ResourceUsageMeasurement(
        measurement_id="meas-test",
        benchmark_id="bench-1",
        experiment_id="exp-1",
        config_id="cfg-1",
        timestamp="2026-08-12T00:00:00Z",
        cpu_utilization_pct=50.0,
        peak_memory_mb=400.0,
        average_memory_mb=350.0,
        execution_duration_sec=3600.0,  # 1 hour run
        total_requests_processed=36000,
        total_tokens_generated=1000000,  # 1M tokens
        concurrency_level=8,
        requests_per_second=10.0,
        tokens_per_second=277.78,
    )

    pricing = ProviderPricingConfig(
        provider="aws",
        instance_type="c7g.xlarge",
        hourly_rate_usd=0.1450,
    )

    estimate = calculator.calculate_cost(measurement, pricing)

    assert estimate.cost_per_benchmark_run == 0.145
    assert estimate.cost_per_million_tokens == 0.145
    assert estimate.throughput_per_dollar > 0.0
    assert estimate.tokens_per_dollar > 0.0
