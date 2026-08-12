"""ArmServe Quality Baseline Comparison Engine.

Compares quality evaluation reports between a baseline configuration and an optimized candidate,
measures score & category deltas, detects quality regressions, and enforces degradation thresholds.
"""

import json
from pathlib import Path
import time
from typing import Any

import structlog
from pydantic import BaseModel, Field

from backend.app.services.quality_scoring_engine import QualityEvaluationReport

logger = structlog.get_logger("backend.app.services.quality_comparator")

COMPARISONS_DIR = Path("storage/quality/comparisons")


class QualityComparisonReport(BaseModel):
    comparison_id: str
    baseline_eval_id: str
    target_eval_id: str
    baseline_config_id: str
    target_config_id: str
    timestamp: str
    baseline_overall_score: float
    target_overall_score: float
    score_difference: float
    percentage_change: float
    category_differences: dict[str, float]
    dimension_differences: dict[str, float]
    allowed_degradation_pct: float = 2.0
    has_regression: bool
    rejected_due_to_degradation: bool
    summary_reasoning: str
    detailed_category_deltas: list[dict[str, Any]]


class QualityComparator:
    """Production Comparator for Evaluating Quality Regressions Against Baseline."""

    def __init__(self, target_dir: Path | None = None) -> None:
        self.target_dir = target_dir or COMPARISONS_DIR
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def compare_evaluations(
        self,
        baseline_report: QualityEvaluationReport,
        target_report: QualityEvaluationReport,
        allowed_degradation_pct: float = 2.0,
    ) -> QualityComparisonReport:
        """Compare baseline and target quality evaluation reports."""
        comp_id = f"qcomp-{int(time.time())}"
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ")

        b_score = baseline_report.overall_quality_score
        t_score = target_report.overall_quality_score

        diff = round(t_score - b_score, 2)
        pct_change = round((diff / max(1.0, b_score)) * 100.0, 2)

        # Category differences
        cat_deltas: dict[str, float] = {}
        cat_details: list[dict[str, Any]] = []

        all_cats = set(baseline_report.category_scores.keys()).union(set(target_report.category_scores.keys()))
        for cat in sorted(all_cats):
            b_cat = baseline_report.category_scores.get(cat, 0.0)
            t_cat = target_report.category_scores.get(cat, 0.0)
            c_diff = round(t_cat - b_cat, 2)
            cat_deltas[cat] = c_diff
            cat_details.append(
                {
                    "category": cat,
                    "baseline_score": b_cat,
                    "target_score": t_cat,
                    "difference": c_diff,
                    "status": "IMPROVED" if c_diff > 0 else ("DEGRADED" if c_diff < 0 else "UNCHANGED"),
                }
            )

        # Dimension differences
        dim_deltas: dict[str, float] = {}
        all_dims = set(baseline_report.dimension_scores.keys()).union(set(target_report.dimension_scores.keys()))
        for dim in sorted(all_dims):
            b_dim = baseline_report.dimension_scores.get(dim, 0.0)
            t_dim = target_report.dimension_scores.get(dim, 0.0)
            dim_deltas[dim] = round(t_dim - b_dim, 2)

        # Determine regression & rejection
        has_regression = diff < 0.0
        degradation_mag = abs(pct_change) if has_regression else 0.0
        rejected = has_regression and (degradation_mag > allowed_degradation_pct)

        if rejected:
            reason = (
                f"REJECTED: Quality score dropped by {abs(diff):.2f} pts ({abs(pct_change):.2f}%), "
                f"exceeding max allowed degradation threshold of {allowed_degradation_pct}%."
            )
        elif has_regression:
            reason = (
                f"ACCEPTED WITH CAUTION: Minor quality degradation of {abs(diff):.2f} pts ({abs(pct_change):.2f}%) "
                f"is within acceptable threshold ({allowed_degradation_pct}%)."
            )
        else:
            reason = f"PASSED: Quality score improved by +{diff:.2f} pts (+{pct_change:.2f}%)."

        report = QualityComparisonReport(
            comparison_id=comp_id,
            baseline_eval_id=baseline_report.evaluation_id,
            target_eval_id=target_report.evaluation_id,
            baseline_config_id=baseline_report.config_id,
            target_config_id=target_report.config_id,
            timestamp=now_str,
            baseline_overall_score=b_score,
            target_overall_score=t_score,
            score_difference=diff,
            percentage_change=pct_change,
            category_differences=cat_deltas,
            dimension_differences=dim_deltas,
            allowed_degradation_pct=allowed_degradation_pct,
            has_regression=has_regression,
            rejected_due_to_degradation=rejected,
            summary_reasoning=reason,
            detailed_category_deltas=cat_details,
        )

        # Persist comparison report
        out_file = self.target_dir / f"{comp_id}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))

        logger.info(
            "Quality comparison completed",
            comp_id=comp_id,
            diff=diff,
            pct_change=pct_change,
            rejected=rejected,
        )
        return report
