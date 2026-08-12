"""Unit tests for Pydantic schemas."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.app.schemas.experiment import ExperimentCreate, PerformanceConstraints, SearchSpace


def test_experiment_create_schema_valid() -> None:
    model_id = uuid4()
    exp = ExperimentCreate(
        name="test-experiment",
        model_id=model_id,
        constraints=PerformanceConstraints(
            max_latency_p99_ms=10.0,
            min_throughput_rps=200.0,
        ),
        search_space=SearchSpace(),
        budget=15,
    )
    assert exp.name == "test-experiment"
    assert exp.budget == 15
    assert exp.constraints.max_latency_p99_ms == 10.0


def test_experiment_create_schema_invalid_budget() -> None:
    model_id = uuid4()
    invalid_budget: int = 0
    with pytest.raises(ValidationError):
        ExperimentCreate(
            name="test-experiment",
            model_id=model_id,
            constraints=PerformanceConstraints(
                max_latency_p99_ms=10.0,
                min_throughput_rps=200.0,
            ),
            budget=invalid_budget,  # Invalid: ge=1 constraint checked at runtime
        )
