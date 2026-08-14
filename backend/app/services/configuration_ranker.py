"""ArmServe Configuration Ranking Engine.

Sorts experiment configurations using composite utility scores, SLA constraint compliance,
and deterministic tie-breaking rules (lower memory > lower thread count). Exports ranked Top-10 lists.
"""

import time
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel

from backend.app.services.constraint_engine import (
    ConstraintEngine,
    ConstraintEvaluationResult,
    ConstraintSpec,
)
from backend.app.services.metrics_normalizer import MetricsNormalizer
from backend.app.services.scoring_engine import ObjectiveWeights, ScoreBreakdown, ScoringEngine

logger = structlog.get_logger("backend.app.services.configuration_ranker")

RANKINGS_DIR = Path("storage/experiments/rankings")


class RankedConfigurationItem(BaseModel):
    rank: int
    config_id: str
    experiment_id: str
    score: float  # [0.0, 100.0]
    is_compliant: bool
    configuration: dict[str, Any]
    metrics_summary: dict[str, Any]
    score_breakdown: ScoreBreakdown
    constraint_evaluation: ConstraintEvaluationResult


class RankingReport(BaseModel):
    ranking_id: str
    timestamp: str
    total_evaluated: int
    compliant_count: int
    rejected_count: int
    top_configurations: list[RankedConfigurationItem]


class ConfigurationRanker:
    """Production Multi-Objective Configuration Ranking Engine."""

    def __init__(self, target_dir: Path | None = None) -> None:
        self.target_dir = target_dir or RANKINGS_DIR
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def rank_experiment_runs(
        self,
        runs_data: list[dict[str, Any]],
        constraint_spec: ConstraintSpec | None = None,
        weights: ObjectiveWeights | None = None,
        top_n: int = 10,
    ) -> RankingReport:
        """Score, filter by SLA constraints, sort by multi-attribute utility score, and rank."""
        if not runs_data:
            now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            return RankingReport(
                ranking_id=f"rank-{int(time.time())}",
                timestamp=now_ts,
                total_evaluated=0,
                compliant_count=0,
                rejected_count=0,
                top_configurations=[],
            )

        # 1. Normalize Dataset Metrics
        snapshots = MetricsNormalizer.normalize_benchmark_runs(runs_data)
        snap_map = {s.run_id: s for s in snapshots}

        eval_items: list[dict[str, Any]] = []

        for run in runs_data:
            exp_id = run.get("experiment_id") or run.get("run_id") or "N/A"
            config_id = run.get("config_id") or "N/A"
            cfg = run.get("configuration") or {}
            metrics = run.get("metrics_summary") or run

            # 2. Evaluate SLA Constraints
            eval_res = ConstraintEngine.evaluate_constraints(metrics, constraint_spec)

            # 3. Compute Composite Score
            snap = snap_map.get(exp_id)
            if snap:
                score_bd = ScoringEngine.compute_experiment_score(snap, weights)
            else:
                score_bd = ScoreBreakdown(
                    latency_score=0.0,
                    throughput_score=0.0,
                    memory_score=0.0,
                    cpu_score=0.0,
                    reliability_score=0.0,
                    individual_scores={},
                    total_score=0.0,
                )

            # If non-compliant with hard SLA constraints, zero out recommendation score
            effective_score = score_bd.total_score if eval_res.is_valid else 0.0

            eval_items.append(
                {
                    "exp_id": exp_id,
                    "config_id": config_id,
                    "configuration": cfg,
                    "metrics_summary": metrics,
                    "is_compliant": eval_res.is_valid,
                    "score": effective_score,
                    "score_breakdown": score_bd,
                    "constraint_evaluation": eval_res,
                    "peak_memory_mb": float(metrics.get("peak_memory_mb", 99999.0)),
                    "thread_count": int(cfg.get("thread_count", 999)),
                }
            )

        # 4. Sort Configurations:
        # Priority 1: is_compliant (True > False)
        # Priority 2: score (descending)
        # Priority 3: peak_memory_mb (ascending)
        # Priority 4: thread_count (ascending)
        eval_items.sort(
            key=lambda x: (
                1 if x["is_compliant"] else 0,
                x["score"],
                -x["peak_memory_mb"],
                -x["thread_count"],
            ),
            reverse=True,
        )

        # 5. Build Top N Rankings
        top_items: list[RankedConfigurationItem] = []
        for rank_idx, item in enumerate(eval_items[:top_n], start=1):
            top_items.append(
                RankedConfigurationItem(
                    rank=rank_idx,
                    config_id=item["config_id"],
                    experiment_id=item["exp_id"],
                    score=item["score"],
                    is_compliant=item["is_compliant"],
                    configuration=item["configuration"],
                    metrics_summary=item["metrics_summary"],
                    score_breakdown=item["score_breakdown"],
                    constraint_evaluation=item["constraint_evaluation"],
                )
            )

        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        ranking_id = f"rank-{int(time.time())}"

        compliant_count = sum(1 for i in eval_items if i["is_compliant"])
        rejected_count = len(eval_items) - compliant_count

        report = RankingReport(
            ranking_id=ranking_id,
            timestamp=now_str,
            total_evaluated=len(eval_items),
            compliant_count=compliant_count,
            rejected_count=rejected_count,
            top_configurations=top_items,
        )

        # Persist ranking report manifest
        out_file = self.target_dir / f"{ranking_id}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))

        logger.info(
            "Generated configuration ranking report",
            ranking_id=ranking_id,
            top_count=len(top_items),
        )
        return report
