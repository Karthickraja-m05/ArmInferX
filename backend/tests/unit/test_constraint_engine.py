"""Unit tests for Constraint Engine."""

import pytest

from backend.app.services.constraint_engine import ConstraintEngine, ConstraintSpec


def test_constraint_engine_acceptance():
    """Test passing all SLA constraints."""
    metrics = {
        "latency_p50_ms": 5.0,
        "latency_p99_ms": 10.0,
        "requests_per_second": 200.0,
        "peak_memory_mb": 400.0,
        "error_rate": 0.0,
    }
    spec = ConstraintSpec(
        max_latency_p50_ms=10.0,
        min_throughput_rps=100.0,
        max_memory_mb=500.0,
    )

    res = ConstraintEngine.evaluate_constraints(metrics, spec)
    assert res.is_valid is True
    assert len(res.violated_constraints) == 0
    assert len(res.accepted_constraints) == 4


def test_constraint_engine_rejection():
    """Test rejecting violated SLA constraints."""
    metrics = {
        "latency_p50_ms": 25.0,  # Violates 10.0ms SLA
        "requests_per_second": 50.0,  # Violates 100.0 RPS SLA
        "peak_memory_mb": 400.0,
    }
    spec = ConstraintSpec(
        max_latency_p50_ms=10.0,
        min_throughput_rps=100.0,
    )

    res = ConstraintEngine.evaluate_constraints(metrics, spec)
    assert res.is_valid is False
    assert "max_latency_p50_ms" in res.violated_constraints
    assert "min_throughput_rps" in res.violated_constraints
