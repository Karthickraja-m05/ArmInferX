"""Unit tests for Quality Response Collector Engine."""

from pathlib import Path
from unittest.mock import patch

import pytest

from backend.app.services.quality_response_collector import QualityResponseCollector


@pytest.mark.asyncio
async def test_quality_response_collector(tmp_path: Path) -> None:
    """Test response collector calling live inference engine and saving responses."""
    collector = QualityResponseCollector(target_dir=tmp_path)
    collector.dataset_manager.target_dir = tmp_path
    collector.dataset_manager._seed_default_datasets_if_empty()

    mock_inf_res = {
        "id": "cmpl-123",
        "object": "text_completion",
        "created": 123456789,
        "model": "qwen2.5-0.5b-instruct",
        "choices": [
            {"text": "The capital of France is Paris.", "index": 0, "finish_reason": "stop"}
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
    }

    with patch.object(collector.inference_engine, "generate_completion", return_value=mock_inf_res):
        record = await collector.collect_dataset_responses(
            config_id="cfg-unit-test",
            experiment_id="exp-unit-test",
            dataset_id="eval-core-v1",
        )

        assert record.config_id == "cfg-unit-test"
        assert len(record.responses) >= 5
        assert record.responses[0].status == "SUCCESS"
        assert "Paris" in record.responses[0].response_text
