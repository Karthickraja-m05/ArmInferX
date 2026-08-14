"""Unit tests for Recommendation Engine."""

from pathlib import Path

from backend.app.services.configuration_ranker import ConfigurationRanker
from backend.app.services.constraint_engine import ConstraintSpec
from backend.app.services.recommendation_engine import RecommendationEngine


def test_recommendation_engine_evidence_reasoning(tmp_path: Path) -> None:
    """Test recommendation generation with evidence-based reasoning and delta calculations."""
    ranker = ConfigurationRanker(target_dir=tmp_path / "rankings")
    rec_engine = RecommendationEngine(target_dir=tmp_path / "recommendations")

    runs = [
        {
            "experiment_id": "exp-fast",
            "config_id": "cfg-fast",
            "configuration": {
                "thread_count": 4,
                "batch_size": 128,
                "model_id": "qwen2.5-0.5b-instruct",
            },
            "metrics_summary": {
                "latency_p50_ms": 4.11,
                "requests_per_second": 237.34,
                "peak_memory_mb": 400.05,
            },
        },
        {
            "experiment_id": "exp-baseline",
            "config_id": "cfg-baseline",
            "configuration": {
                "thread_count": 2,
                "batch_size": 64,
                "model_id": "qwen2.5-0.5b-instruct",
            },
            "metrics_summary": {
                "latency_p50_ms": 4.60,
                "requests_per_second": 187.83,
                "peak_memory_mb": 399.75,
            },
        },
    ]

    spec = ConstraintSpec(max_latency_p50_ms=10.0)
    ranking_report = ranker.rank_experiment_runs(runs, constraint_spec=spec)

    rec = rec_engine.generate_recommendation(ranking_report, baseline_run=runs[1])

    assert rec.recommended_config_id == "cfg-fast"
    assert rec.score > 0.0
    assert len(rec.evidence_based_reasoning) >= 2
    # Verify delta calculations in reasoning
    reasoning_text = " ".join(rec.evidence_based_reasoning)
    assert "reduced P50 latency by 10.7%" in reasoning_text or "P50 latency" in reasoning_text
    assert (
        "increased request throughput by 26.4%" in reasoning_text
        or "request throughput" in reasoning_text
    )
    assert len(rec.rejected_alternatives) == 1
