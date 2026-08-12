"""ArmServe Quality Reporting Engine.

Generates evidence-based quality reports in Markdown, JSON, and CSV formats based on
measured evaluation scores and baseline comparison results.
"""

import csv
import io
import json
from pathlib import Path
import time
from typing import Any

import structlog

from backend.app.services.quality_comparator import QualityComparisonReport
from backend.app.services.quality_scoring_engine import QualityEvaluationReport

logger = structlog.get_logger("backend.app.services.quality_reporter")

REPORTS_DIR = Path("storage/quality/reports")


class QualityReporter:
    """Production Multi-Format Quality Reporting Engine."""

    def __init__(self, target_dir: Path | None = None) -> None:
        self.target_dir = target_dir or REPORTS_DIR
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def generate_markdown_report(
        self,
        eval_report: QualityEvaluationReport,
        comp_report: QualityComparisonReport | None = None,
    ) -> str:
        """Generate structured Markdown quality report."""
        lines = [
            f"# ArmServe Quality Evaluation Report: `{eval_report.evaluation_id}`",
            "",
            f"**Timestamp**: {eval_report.timestamp}  ",
            f"**Target Config ID**: `{eval_report.config_id}`  ",
            f"**Experiment ID**: `{eval_report.experiment_id}`  ",
            f"**Overall Quality Score**: **{eval_report.overall_quality_score} / 100.0**  ",
            f"**Evaluation Result**: {'✅ PASS' if eval_report.passed else '❌ FAIL'}  ",
            "",
            "---",
            "",
            "## 1. Dimension Score Breakdown",
            "",
            "| Quality Dimension | Score | Status |",
            "|---|---|---|",
        ]

        for dim, score in eval_report.dimension_scores.items():
            status = "✅ PASS" if score >= 75.0 else "⚠️ WARN"
            lines.append(f"| `{dim}` | **{score:.1f}%** | {status} |")

        lines.extend([
            "",
            "## 2. Category Score Breakdown",
            "",
            "| Evaluation Category | Measured Score |",
            "|---|---|",
        ])

        for cat, score in eval_report.category_scores.items():
            lines.append(f"| `{cat}` | **{score:.1f}%** |")

        if comp_report:
            lines.extend([
                "",
                "---",
                "",
                "## 3. Baseline Comparison Summary",
                "",
                f"- **Baseline Config ID**: `{comp_report.baseline_config_id}`",
                f"- **Baseline Quality Score**: {comp_report.baseline_overall_score} / 100.0",
                f"- **Target Quality Score**: {comp_report.target_overall_score} / 100.0",
                f"- **Score Difference ($\Delta Q$)**: `{comp_report.score_difference:+.2f}` ({comp_report.percentage_change:+.2f}%)",
                f"- **Regression Status**: {'⚠️ REGRESSION DETECTED' if comp_report.has_regression else '✅ NO REGRESSION'}",
                f"- **Deployment Decision**: {'❌ REJECTED' if comp_report.rejected_due_to_degradation else '✅ APPROVED'}",
                "",
                f"> **Evidence-Based Reasoning**: {comp_report.summary_reasoning}",
                "",
                "### Category Differences ($\Delta$ Baseline)",
                "",
                "| Category | Baseline Score | Target Score | $\Delta$ Change | Status |",
                "|---|---|---|---|---|",
            ])

            for item in comp_report.detailed_category_deltas:
                lines.append(
                    f"| `{item['category']}` | {item['baseline_score']:.1f}% | {item['target_score']:.1f}% | "
                    f"`{item['difference']:+.1f}%` | {item['status']} |"
                )

        lines.extend([
            "",
            "---",
            "",
            "## 4. Evaluated Prompt Audit",
            "",
            "| Prompt ID | Category | Total Score | Correctness | Completeness | Formatting | Result |",
            "|---|---|---|---|---|---|---|",
        ])

        for ps in eval_report.prompt_scores:
            res_str = "✅ PASS" if ps.passed else "❌ FAIL"
            lines.append(
                f"| `{ps.prompt_id}` | `{ps.category}` | **{ps.total_prompt_score:.1f}** | "
                f"{ps.correctness_score:.1f}% | {ps.completeness_score:.1f}% | {ps.formatting_score:.1f}% | {res_str} |"
            )

        content = "\n".join(lines)
        out_file = self.target_dir / f"report_{eval_report.evaluation_id}.md"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(content)

        return content

    def generate_json_report(
        self,
        eval_report: QualityEvaluationReport,
        comp_report: QualityComparisonReport | None = None,
    ) -> dict[str, Any]:
        """Generate structured JSON quality report."""
        report_data = {
            "report_id": f"qrep-{eval_report.evaluation_id}",
            "timestamp": eval_report.timestamp,
            "evaluation": eval_report.model_dump(),
            "comparison": comp_report.model_dump() if comp_report else None,
        }

        out_file = self.target_dir / f"report_{eval_report.evaluation_id}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        return report_data

    def generate_csv_report(self, eval_report: QualityEvaluationReport) -> str:
        """Generate CSV export of prompt-level quality metrics."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "evaluation_id",
            "config_id",
            "experiment_id",
            "prompt_id",
            "category",
            "total_score",
            "correctness_score",
            "completeness_score",
            "instruction_score",
            "formatting_score",
            "passed",
        ])

        for ps in eval_report.prompt_scores:
            writer.writerow([
                eval_report.evaluation_id,
                eval_report.config_id,
                eval_report.experiment_id,
                ps.prompt_id,
                ps.category,
                ps.total_prompt_score,
                ps.correctness_score,
                ps.completeness_score,
                ps.instruction_score,
                ps.formatting_score,
                ps.passed,
            ])

        content = output.getvalue()
        out_file = self.target_dir / f"report_{eval_report.evaluation_id}.csv"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(content)

        return content
