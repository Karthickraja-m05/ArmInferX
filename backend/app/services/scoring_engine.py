"""ArmServe Optimization Scoring Engine.

Computes weighted optimization scores from normalized metrics, supports configurable
objective weights, and generates detailed individual metric score breakdowns.
"""

from typing import Any
import structlog
from pydantic import BaseModel, Field

from backend.app.services.metrics_normalizer import MetricsNormalizer, NormalizedMetricsSnapshot

logger = structlog.get_logger("backend.app.services.scoring_engine")


class ObjectiveWeights(BaseModel):
    latency: float = Field(0.35, ge=0.0, description="Weight for latency metrics.")
    throughput: float = Field(0.35, ge=0.0, description="Weight for RPS/TPS throughput metrics.")
    memory: float = Field(0.15, ge=0.0, description="Weight for RAM RSS memory usage.")
    cpu: float = Field(0.10, ge=0.0, description="Weight for CPU utilization.")
    reliability: float = Field(0.05, ge=0.0, description="Weight for error rate / success rate.")

    def normalize_weights(self) -> "ObjectiveWeights":
        total = self.latency + self.throughput + self.memory + self.cpu + self.reliability
        if total <= 0:
            return ObjectiveWeights(latency=0.35, throughput=0.35, memory=0.15, cpu=0.10, reliability=0.05)
        return ObjectiveWeights(
            latency=round(self.latency / total, 4),
            throughput=round(self.throughput / total, 4),
            memory=round(self.memory / total, 4),
            cpu=round(self.cpu / total, 4),
            reliability=round(self.reliability / total, 4),
        )


class ScoreBreakdown(BaseModel):
    latency_score: float
    throughput_score: float
    memory_score: float
    cpu_score: float
    reliability_score: float
    individual_scores: dict[str, float]
    total_score: float  # [0.0, 100.0]


class ScoringEngine:
    """Production Multi-Objective Weighted Scoring Engine."""

    @classmethod
    def compute_experiment_score(
        cls,
        normalized_snapshot: NormalizedMetricsSnapshot,
        weights: ObjectiveWeights | None = None,
        error_rate: float = 0.0,
    ) -> ScoreBreakdown:
        """Compute reproducible weighted composite score and detailed metric breakdown."""
        w = (weights or ObjectiveWeights()).normalize_weights()

        norm_map = {m.metric_name: m.normalized_value for m in normalized_snapshot.normalized_metrics}

        # Sub-component scores
        lat_val = norm_map.get("latency_p50_ms", 1.0)
        tp_val = norm_map.get("requests_per_second", norm_map.get("tokens_per_second", 0.0))
        mem_val = norm_map.get("peak_memory_mb", 1.0)
        cpu_val = norm_map.get("cpu_utilization_percent", 1.0)
        rel_val = max(0.0, min(1.0, 1.0 - error_rate))

        composite_val = (
            lat_val * w.latency
            + tp_val * w.throughput
            + mem_val * w.memory
            + cpu_val * w.cpu
            + rel_val * w.reliability
        )

        total_score = round(composite_val * 100.0, 2)

        return ScoreBreakdown(
            latency_score=round(lat_val * 100.0, 2),
            throughput_score=round(tp_val * 100.0, 2),
            memory_score=round(mem_val * 100.0, 2),
            cpu_score=round(cpu_val * 100.0, 2),
            reliability_score=round(rel_val * 100.0, 2),
            individual_scores={k: round(v * 100.0, 2) for k, v in norm_map.items()},
            total_score=total_score,
        )
