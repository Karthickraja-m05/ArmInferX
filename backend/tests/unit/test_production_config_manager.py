"""Unit tests for Production Configuration Manager."""

import pytest
from backend.app.services.production_config_manager import production_config_manager


def test_validate_valid_configuration():
    """Test validating a valid production runtime configuration."""
    cfg = {
        "model_id": "qwen2.5-0.5b-instruct",
        "thread_count": 4,
        "batch_size": 32,
        "context_length": 2048,
        "temperature": 0.7,
        "max_tokens": 512,
        "quantization_variant": "Q4_K_M",
        "environment": "production",
    }
    is_valid, errors, validated = production_config_manager.validate_configuration(cfg)
    assert is_valid is True
    assert len(errors) == 0
    assert validated["thread_count"] == 4
    assert validated["batch_size"] == 32


def test_validate_invalid_configuration():
    """Test that out-of-bounds parameters fail validation."""
    cfg = {
        "model_id": "qwen2.5-0.5b-instruct",
        "thread_count": -5,  # Invalid
        "batch_size": 10000,  # Exceeds max
        "temperature": 5.0,  # Exceeds max 2.0
    }
    is_valid, errors, validated = production_config_manager.validate_configuration(cfg)
    assert is_valid is False
    assert len(errors) > 0


def test_compare_configurations():
    """Test comparing two configuration dictionaries."""
    cfg1 = {"model_id": "qwen2.5", "thread_count": 4, "batch_size": 32}
    cfg2 = {"model_id": "qwen2.5", "thread_count": 8, "batch_size": 32, "extra": "val"}

    res = production_config_manager.compare_configurations(cfg1, cfg2)
    assert res["match"] is False
    assert len(res["differences"]) == 2  # thread_count modified, extra added

    diff_map = {d["parameter"]: d for d in res["differences"]}
    assert diff_map["thread_count"]["status"] == "MODIFIED"
    assert diff_map["thread_count"]["val1"] == 4
    assert diff_map["thread_count"]["val2"] == 8
    assert diff_map["extra"]["status"] == "ADDED"
