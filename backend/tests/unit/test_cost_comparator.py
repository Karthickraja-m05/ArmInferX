"""Unit tests for Cost Comparator Engine."""

from pathlib import Path

from backend.app.services.cost_calculator import CostEstimate, ProviderPricingConfig
from backend.app.services.cost_comparator import CostComparator


def test_cost_comparator_savings(tmp_path: Path) -> None:
    """Test cost comparison, percentage savings calculation, and ranking."""
    comparator = CostComparator(target_dir=tmp_path)

    pricing = ProviderPricingConfig()

    b_est = CostEstimate(
        calculation_id="calc-base",
        measurement_id="meas-base",
        config_id="cfg-base",
        experiment_id="exp-base",
        timestamp="2026-08-12T00:00:00Z",
        pricing=pricing,
        cost_per_benchmark_run=0.10,
        cost_per_minute=0.002,
        cost_per_hour=0.145,
        cost_per_request=0.0001,
        cost_per_token=0.000001,
        cost_per_million_tokens=1.00,  # $1.00 / 1M tokens
        throughput_per_dollar=100.0,
        tokens_per_dollar=1000.0,
        assumptions=[],
    )

    t_est = CostEstimate(
        calculation_id="calc-target",
        measurement_id="meas-target",
        config_id="cfg-target",
        experiment_id="exp-target",
        timestamp="2026-08-12T00:05:00Z",
        pricing=pricing,
        cost_per_benchmark_run=0.07,
        cost_per_minute=0.002,
        cost_per_hour=0.145,
        cost_per_request=0.00007,
        cost_per_token=0.0000007,
        cost_per_million_tokens=0.70,  # $0.70 / 1M tokens (30% savings)
        throughput_per_dollar=140.0,
        tokens_per_dollar=1400.0,
        assumptions=[],
    )

    comp = comparator.compare_estimates(b_est, t_est)

    assert comp.percentage_cost_savings == 30.0
    assert comp.more_cost_effective is True
    assert "reduces cost per 1M tokens" in comp.summary_reasoning

    ranked = comparator.rank_configurations_by_cost([b_est, t_est])
    assert ranked[0].config_id == "cfg-target"
