"""Unit tests for Metrics Normalization Engine."""

import pytest

from backend.app.services.metrics_normalizer import MetricsNormalizer


def test_normalize_single_value_direct():
    """Test direct min-max normalization where higher is better (throughput)."""
    # 50 req/s in range [0, 100] -> 0.5
    val = MetricsNormalizer.normalize_single_value(50.0, min_val=0.0, max_val=100.0, lower_is_better=False)
    assert val == 0.5

    # 100 req/s in range [0, 100] -> 1.0
    val_max = MetricsNormalizer.normalize_single_value(100.0, min_val=0.0, max_val=100.0, lower_is_better=False)
    assert val_max == 1.0


def test_normalize_single_value_inverted():
    """Test inverted min-max normalization where lower is better (latency)."""
    # 10ms in range [10ms, 110ms] -> 1.0 (lowest latency is best score)
    best_lat = MetricsNormalizer.normalize_single_value(10.0, min_val=10.0, max_val=110.0, lower_is_better=True)
    assert best_lat == 1.0

    # 110ms in range [10ms, 110ms] -> 0.0 (highest latency is worst score)
    worst_lat = MetricsNormalizer.normalize_single_value(110.0, min_val=10.0, max_val=110.0, lower_is_better=True)
    assert worst_lat == 0.0


def test_normalize_benchmark_runs_dataset():
    """Test dataset min-max scaling across multiple benchmark runs."""
    runs = [
        {
            "run_id": "run-fast",
            "metrics_summary": {
                "latency_p50_ms": 5.0,
                "requests_per_second": 200.0,
                "peak_memory_mb": 400.0,
            },
        },
        {
            "run_id": "run-slow",
            "metrics_summary": {
                "latency_p50_ms": 25.0,
                "requests_per_second": 50.0,
                "peak_memory_mb": 800.0,
            },
        },
    ]

    snapshots = MetricsNormalizer.normalize_benchmark_runs(runs)
    assert len(snapshots) == 2

    fast_snap = next(s for s in snapshots if s.run_id == "run-fast")
    slow_snap = next(s for s in snapshots if s.run_id == "run-slow")

    # Fast run should have higher composite score
    assert fast_snap.composite_score > slow_snap.composite_score

    # Fast run latency (5.0ms vs 25.0ms) should yield normalized score 1.0
    fast_lat = next(m for m in fast_snap.normalized_metrics if m.metric_name == "latency_p50_ms")
    assert fast_lat.normalized_value == 1.0
