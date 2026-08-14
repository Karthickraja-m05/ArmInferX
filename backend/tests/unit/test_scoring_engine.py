"""Unit tests for Scoring Engine."""

from backend.app.services.metrics_normalizer import NormalizedMetricItem, NormalizedMetricsSnapshot
from backend.app.services.scoring_engine import ObjectiveWeights, ScoringEngine


def test_objective_weights_normalization():
    """Test weight normalization."""
    w = ObjectiveWeights(
        latency=2.0, throughput=2.0, memory=1.0, cpu=0.0, reliability=0.0
    ).normalize_weights()
    assert w.latency == 0.4
    assert w.throughput == 0.4
    assert w.memory == 0.2


def test_scoring_engine_computation():
    """Test composite utility score computation."""
    snap = NormalizedMetricsSnapshot(
        run_id="test-run-1",
        timestamp="2026-08-12T00:00:00Z",
        normalized_metrics=[
            NormalizedMetricItem(
                metric_name="latency_p50_ms",
                raw_value=5.0,
                normalized_value=1.0,
                lower_is_better=True,
                unit="ms",
            ),
            NormalizedMetricItem(
                metric_name="requests_per_second",
                raw_value=200.0,
                normalized_value=1.0,
                lower_is_better=False,
                unit="req/s",
            ),
            NormalizedMetricItem(
                metric_name="peak_memory_mb",
                raw_value=400.0,
                normalized_value=1.0,
                lower_is_better=True,
                unit="MB",
            ),
            NormalizedMetricItem(
                metric_name="cpu_utilization_percent",
                raw_value=50.0,
                normalized_value=1.0,
                lower_is_better=True,
                unit="%",
            ),
        ],
        composite_score=100.0,
    )

    bd = ScoringEngine.compute_experiment_score(snap)
    assert bd.total_score == 100.0
    assert bd.latency_score == 100.0
    assert bd.throughput_score == 100.0
