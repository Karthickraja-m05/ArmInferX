"""Unit tests for Quality Scoring Engine."""

from pathlib import Path

from backend.app.services.quality_response_collector import EvaluationCollectionRecord, ResponseItem
from backend.app.services.quality_scoring_engine import QualityScoringEngine


def test_quality_scoring_engine(tmp_path: Path) -> None:
    """Test scoring response collection record across dimensions and categories."""
    engine = QualityScoringEngine(target_dir=tmp_path)

    responses = [
        ResponseItem(
            prompt_id="p-1",
            category="question_answering",
            prompt="What is the capital of France?",
            response_text="The capital of France is Paris.",
            latency_ms=10.0,
            prompt_tokens=8,
            completion_tokens=6,
            status="SUCCESS",
            expected_behavior={"exact_match_contains": ["Paris"]},
        ),
        ResponseItem(
            prompt_id="p-2",
            category="coding",
            prompt="Write python code.",
            response_text="```python\ndef foo():\n    return True\n```",
            latency_ms=15.0,
            prompt_tokens=5,
            completion_tokens=10,
            status="SUCCESS",
            expected_behavior={"syntax_check": "python", "expected_keywords": ["def foo"]},
        ),
    ]

    record = EvaluationCollectionRecord(
        collection_id="coll-test-1",
        dataset_id="eval-core-v1",
        config_id="cfg-1",
        experiment_id="exp-1",
        timestamp="2026-08-12T00:00:00Z",
        responses=responses,
    )

    report = engine.evaluate_collection_record(record)

    assert report.overall_quality_score > 80.0
    assert report.passed is True
    assert "question_answering" in report.category_scores
    assert "coding" in report.category_scores
    assert report.dimension_scores["correctness"] == 100.0
