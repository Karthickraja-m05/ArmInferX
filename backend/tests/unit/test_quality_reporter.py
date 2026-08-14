"""Unit tests for Quality Reporting Engine."""

from pathlib import Path

from backend.app.services.quality_comparator import QualityComparisonReport
from backend.app.services.quality_reporter import QualityReporter
from backend.app.services.quality_scoring_engine import PromptQualityScore, QualityEvaluationReport


def test_quality_reporter_multi_format(tmp_path: Path) -> None:
    """Test generating Markdown, JSON, and CSV quality evaluation reports."""
    reporter = QualityReporter(target_dir=tmp_path)

    eval_report = QualityEvaluationReport(
        evaluation_id="eval-report-test",
        collection_id="coll-1",
        config_id="cfg-1",
        experiment_id="exp-1",
        timestamp="2026-08-12T00:00:00Z",
        overall_quality_score=92.5,
        passed=True,
        category_scores={"reasoning": 92.5},
        dimension_scores={"correctness": 95.0, "completeness": 90.0},
        prompt_scores=[
            PromptQualityScore(
                prompt_id="p-1",
                category="reasoning",
                correctness_score=95.0,
                completeness_score=90.0,
                instruction_score=90.0,
                formatting_score=95.0,
                total_prompt_score=92.5,
                passed=True,
                evaluation_logs=["Pass"],
            )
        ],
    )

    comp_report = QualityComparisonReport(
        comparison_id="qcomp-1",
        baseline_eval_id="eval-base",
        target_eval_id="eval-report-test",
        baseline_config_id="cfg-base",
        target_config_id="cfg-1",
        timestamp="2026-08-12T00:00:00Z",
        baseline_overall_score=90.0,
        target_overall_score=92.5,
        score_difference=2.5,
        percentage_change=2.78,
        category_differences={"reasoning": 2.5},
        dimension_differences={"correctness": 5.0},
        allowed_degradation_pct=2.0,
        has_regression=False,
        rejected_due_to_degradation=False,
        summary_reasoning="PASSED: Quality score improved.",
        detailed_category_deltas=[
            {
                "category": "reasoning",
                "baseline_score": 90.0,
                "target_score": 92.5,
                "difference": 2.5,
                "status": "IMPROVED",
            }
        ],
    )

    md = reporter.generate_markdown_report(eval_report, comp_report)
    assert "# ArmServe Quality Evaluation Report" in md
    assert "Overall Quality Score" in md

    json_data = reporter.generate_json_report(eval_report, comp_report)
    assert json_data["report_id"] == "qrep-eval-report-test"

    csv_text = reporter.generate_csv_report(eval_report)
    assert "evaluation_id,config_id,experiment_id" in csv_text
