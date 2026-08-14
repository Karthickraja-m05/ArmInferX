"""Unit tests for Quality Comparator Engine."""

from pathlib import Path

from backend.app.services.quality_comparator import QualityComparator
from backend.app.services.quality_scoring_engine import QualityEvaluationReport


def test_quality_comparator(tmp_path: Path) -> None:
    """Test baseline comparison, regression detection, and degradation threshold enforcement."""
    comparator = QualityComparator(target_dir=tmp_path)

    b_report = QualityEvaluationReport(
        evaluation_id="eval-base",
        collection_id="coll-base",
        config_id="cfg-base",
        experiment_id="exp-base",
        timestamp="2026-08-12T00:00:00Z",
        overall_quality_score=95.0,
        passed=True,
        category_scores={"reasoning": 95.0, "coding": 95.0},
        dimension_scores={"correctness": 95.0, "completeness": 95.0},
        prompt_scores=[],
    )

    t_report = QualityEvaluationReport(
        evaluation_id="eval-target",
        collection_id="coll-target",
        config_id="cfg-target",
        experiment_id="exp-target",
        timestamp="2026-08-12T00:05:00Z",
        overall_quality_score=90.0,  # 5.26% drop -> exceeds 2.0% threshold
        passed=True,
        category_scores={"reasoning": 90.0, "coding": 90.0},
        dimension_scores={"correctness": 90.0, "completeness": 90.0},
        prompt_scores=[],
    )

    comp = comparator.compare_evaluations(b_report, t_report, allowed_degradation_pct=2.0)

    assert comp.score_difference == -5.0
    assert comp.has_regression is True
    assert comp.rejected_due_to_degradation is True
    assert "REJECTED" in comp.summary_reasoning
