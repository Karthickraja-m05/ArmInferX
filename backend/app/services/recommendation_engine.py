"""ArmServe Optimization Recommendation Engine.

Analyzes ranked experiment results, selects the optimal configuration satisfying SLA constraints,
computes empirical delta improvements against baseline, and generates evidence-based explanations.
"""

import json
from pathlib import Path
import time
from typing import Any

import structlog
from pydantic import BaseModel, Field

from backend.app.services.configuration_ranker import ConfigurationRanker, RankedConfigurationItem, RankingReport
from backend.app.services.constraint_engine import ConstraintSpec
from backend.app.services.scoring_engine import ObjectiveWeights

logger = structlog.get_logger("backend.app.services.recommendation_engine")

RECOMMENDATIONS_DIR = Path("storage/experiments/recommendations")


class AlternativeSummary(BaseModel):
    config_id: str
    experiment_id: str
    score: float
    reason_not_selected: str


class OptimizationRecommendation(BaseModel):
    recommendation_id: str
    timestamp: str
    target_model_id: str
    recommended_config_id: str
    recommended_experiment_id: str
    score: float  # [0.0, 100.0]
    configuration: dict[str, Any]
    metrics_summary: dict[str, Any]
    evidence_based_reasoning: list[str]
    trade_offs: list[str]
    rejected_alternatives: list[AlternativeSummary]


class RecommendationEngine:
    """Production Evidence-Based Optimization Recommendation Engine."""

    def __init__(self, target_dir: Path | None = None) -> None:
        self.target_dir = target_dir or RECOMMENDATIONS_DIR
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def generate_recommendation(
        self,
        ranking_report: RankingReport,
        baseline_run: dict[str, Any] | None = None,
    ) -> OptimizationRecommendation:
        """Derive evidence-based recommendation with quantitative explanations and trade-offs."""
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        rec_id = f"rec-{int(time.time())}"

        if not ranking_report.top_configurations:
            return OptimizationRecommendation(
                recommendation_id=rec_id,
                timestamp=now_str,
                target_model_id="unknown",
                recommended_config_id="none",
                recommended_experiment_id="none",
                score=0.0,
                configuration={},
                metrics_summary={},
                evidence_based_reasoning=["No valid experiment configurations evaluated."],
                trade_offs=["Unable to compute trade-offs due to lack of experiment data."],
                rejected_alternatives=[],
            )

        # 1. Identify Top Compliant Configuration
        compliant_items = [item for item in ranking_report.top_configurations if item.is_compliant]

        if not compliant_items:
            best_item = ranking_report.top_configurations[0]
            is_fallback = True
        else:
            best_item = compliant_items[0]
            is_fallback = False

        cfg = best_item.configuration or {}
        metrics = best_item.metrics_summary or {}
        model_id = str(cfg.get("model_id") or "qwen2.5-0.5b-instruct")

        # 2. Derive Evidence-Based Reasoning & Empirical Delta Improvements
        reasoning: list[str] = []

        if is_fallback:
            reasoning.append(
                f"[WARNING] No configuration satisfied 100% of mandatory SLA constraints. "
                f"Selecting top relative performer '{best_item.config_id}' (Score: {best_item.score:.1f}/100)."
            )
        else:
            reasoning.append(
                f"Selected configuration '{best_item.config_id}' as the top-performing recommendation "
                f"with composite utility score {best_item.score:.1f}/100."
            )

        # Quantitative Deltas against Baseline (if baseline provided)
        if isinstance(baseline_run, dict):
            b_metrics = baseline_run.get("metrics_summary") if isinstance(baseline_run.get("metrics_summary"), dict) else baseline_run
            if not isinstance(b_metrics, dict):
                b_metrics = {}

            b_lat = float(b_metrics.get("latency_p50_ms") or 0.0)
            r_lat = float(metrics.get("latency_p50_ms") or 0.0)
            if b_lat > 0 and r_lat > 0:
                lat_delta_pct = round(((b_lat - r_lat) / b_lat) * 100.0, 1)
                lat_direction = "reduced" if lat_delta_pct >= 0 else "increased"
                reasoning.append(
                    f"Measured Latency: {lat_direction.capitalize()} P50 latency by {abs(lat_delta_pct)}% "
                    f"({b_lat:.2f}ms -> {r_lat:.2f}ms)."
                )

            b_rps = float(b_metrics.get("requests_per_second") or 0.0)
            r_rps = float(metrics.get("requests_per_second") or 0.0)
            if b_rps > 0 and r_rps > 0:
                rps_delta_pct = round(((r_rps - b_rps) / b_rps) * 100.0, 1)
                rps_direction = "increased" if rps_delta_pct >= 0 else "decreased"
                reasoning.append(
                    f"Measured Throughput: {rps_direction.capitalize()} request throughput by {abs(rps_delta_pct)}% "
                    f"({b_rps:.1f} req/s -> {r_rps:.1f} req/s)."
                )

            b_ram = float(b_metrics.get("peak_memory_mb") or 0.0)
            r_ram = float(metrics.get("peak_memory_mb") or 0.0)
            if b_ram > 0 and r_ram > 0:
                ram_delta_pct = round(((r_ram - b_ram) / b_ram) * 100.0, 1)
                reasoning.append(
                    f"Memory Footprint: Peak RSS memory changed by {ram_delta_pct:+.1f}% "
                    f"({b_ram:.1f}MB -> {r_ram:.1f}MB)."
                )
        else:
            p50 = metrics.get("latency_p50_ms", "N/A")
            rps = metrics.get("requests_per_second", "N/A")
            ram = metrics.get("peak_memory_mb", "N/A")
            reasoning.append(
                f"Measured Performance: Achieved sub-{p50}ms P50 latency, {rps} req/s throughput, "
                f"and {ram} MB peak RAM usage on AWS Graviton CPU inference."
            )

        # 3. Derive Trade-Offs
        trade_offs: list[str] = []
        threads = int(cfg.get("thread_count", 1))
        batch = int(cfg.get("batch_size", 1))

        if threads > 4:
            trade_offs.append(f"Higher CPU Allocation: Uses {threads} threads, increasing vCPU core utilization.")
        if batch > 64:
            trade_offs.append(f"Larger Batch Size ({batch}): Increases throughput but slightly elevates TTFT under queue pressure.")

        if not trade_offs:
            trade_offs.append("Balanced Resource Allocation: Maintains optimal thread count and memory efficiency.")

        # 4. Rejected Alternatives
        rejected: list[AlternativeSummary] = []
        for alt in ranking_report.top_configurations:
            if alt.config_id == best_item.config_id:
                continue

            if not alt.is_compliant:
                v_str = ", ".join(alt.constraint_evaluation.violated_constraints)
                reason = f"Violated SLA constraints: {v_str}"
            else:
                reason = f"Lower utility score ({alt.score:.1f} vs {best_item.score:.1f})"

            rejected.append(
                AlternativeSummary(
                    config_id=alt.config_id,
                    experiment_id=alt.experiment_id,
                    score=alt.score,
                    reason_not_selected=reason,
                )
            )

        rec = OptimizationRecommendation(
            recommendation_id=rec_id,
            timestamp=now_str,
            target_model_id=model_id,
            recommended_config_id=best_item.config_id,
            recommended_experiment_id=best_item.experiment_id,
            score=best_item.score,
            configuration=cfg,
            metrics_summary=metrics,
            evidence_based_reasoning=reasoning,
            trade_offs=trade_offs,
            rejected_alternatives=rejected,
        )

        # Persist recommendation manifest
        out_file = self.target_dir / f"{rec_id}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(rec.model_dump_json(indent=2))

        logger.info("Generated optimization recommendation", rec_id=rec_id, config_id=best_item.config_id)
        return rec
