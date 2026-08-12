"""Unit tests for Experiment Configuration Generator."""

import pytest

from backend.app.services.experiment_generator import ConfigurationGenerator, ParameterRangeSpec


def test_generator_valid_configurations():
    """Test generating valid, deduplicated configurations."""
    generator = ConfigurationGenerator()
    spec = ParameterRangeSpec(
        thread_counts=[1, 2, 4],
        batch_sizes=[64, 128],
        context_lengths=[2048],
        temperatures=[0.0],
        max_tokens_list=[128],
    )

    configs = generator.generate_configurations(spec)
    assert len(configs) == 6  # 3 threads * 2 batches * 1 context * 1 temp * 1 max_tok
    assert all(c.config_id.startswith("cfg-") for c in configs)
    assert len({c.hash_signature for c in configs}) == 6


def test_generator_deduplication():
    """Test preventing duplicate configuration generation."""
    generator = ConfigurationGenerator()
    spec = ParameterRangeSpec(
        thread_counts=[2],
        batch_sizes=[128],
        context_lengths=[2048],
        temperatures=[0.7],
        max_tokens_list=[256],
    )

    # First run generates 1 config
    configs1 = generator.generate_configurations(spec)
    # Second identical run generates 0 configs (all deduplicated)
    configs2 = generator.generate_configurations(spec)

    assert len(configs2) == 0


def test_generator_invalid_constraints():
    """Test filtering invalid parameter constraints."""
    generator = ConfigurationGenerator()
    
    # Batch size > Context length -> Invalid
    invalid_params = {
        "thread_count": 4,
        "batch_size": 4096,
        "context_length": 2048,
        "temperature": 0.7,
    }
    assert generator.validate_parameter_constraints(invalid_params) is False
