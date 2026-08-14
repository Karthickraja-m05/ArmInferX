"""ArmServe Metrics Normalization Engine.

Performs min-max scaling, direction inversion (for latency, memory, and CPU metrics),
and persistence of normalized score vectors without mutating raw benchmark data.
"""

from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel

logger = structlog.get_logger("backend.app.services.metrics_normalizer")

NORMALIZED_DIR = Path("storage/experiments/normalized")


class NormalizedMetricItem(BaseModel):
    metric_name: str
    raw_value: float
    normalized_value: float  # [0.0, 1.0] scale where 1.0 is best
    lower_is_better: bool
    unit: str


class NormalizedMetricsSnapshot(BaseModel):
    run_id: str
    timestamp: str
    normalized_metrics: list[NormalizedMetricItem]
    composite_score: float  # Weighted score [0.0, 100.0]


class MetricsNormalizer:
    """Production Min-Max Normalization Engine with Direction Inversion."""

    def __init__(self) -> None:
        NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def normalize_single_value(
        value: float, min_val: float, max_val: float, lower_is_better: bool = False
    ) -> float:
        """Min-Max scale a single metric value into [0.0, 1.0]. Invert if lower is better."""
        if max_val <= min_val:
            return 1.0  # Equal range defaults to perfect score

        # Direct Min-Max Scaling
        norm = (value - min_val) / (max_val - min_val)
        norm = max(0.0, min(1.0, norm))

        if lower_is_better:
            norm = 1.0 - norm

        return round(norm, 4)

    @classmethod
    def normalize_benchmark_runs(
        cls,
        runs_data: list[dict[str, Any]],
        weights: dict[str, float] | None = None,
        target_dir: Path | None = None,
    ) -> list[NormalizedMetricsSnapshot]:
        """Normalize a collection of benchmark runs relative to min-max bounds across the dataset."""
        if not runs_data:
            return []

        out_dir = target_dir or NORMALIZED_DIR
        out_dir.mkdir(parents=True, exist_ok=True)

        default_weights = {
            "latency_p50_ms": 0.35,
            "requests_per_second": 0.35,
            "tokens_per_second": 0.15,
            "peak_memory_mb": 0.15,
        }
        w = weights or default_weights

        # Direction mapping (True if lower value is superior)
        metric_directions = {
            "latency_p50_ms": True,
            "latency_p90_ms": True,
            "latency_p99_ms": True,
            "time_to_first_token_ms": True,
            "peak_memory_mb": True,
            "cpu_utilization_percent": True,
            "requests_per_second": False,
            "tokens_per_second": False,
        }

        metric_units = {
            "latency_p50_ms": "ms",
            "latency_p90_ms": "ms",
            "latency_p99_ms": "ms",
            "time_to_first_token_ms": "ms",
            "peak_memory_mb": "MB",
            "cpu_utilization_percent": "%",
            "requests_per_second": "req/s",
            "tokens_per_second": "tok/s",
        }

        # 1. Compute Dataset Min and Max Bounds for each metric
        bounds: dict[str, tuple[float, float]] = {}
        for metric_key, _ in metric_directions.items():
            vals: list[float] = []
            for run in runs_data:
                if not isinstance(run, dict):
                    continue
                m_summary = (
                    run.get("metrics_summary")
                    if isinstance(run.get("metrics_summary"), dict)
                    else {}
                )
                v = run.get(metric_key) or (
                    m_summary.get(metric_key) if isinstance(m_summary, dict) else None
                )
                if v is not None:
                    vals.append(float(v))
            if vals:
                bounds[metric_key] = (min(vals), max(vals))

        # 2. Normalize Each Run
        snapshots: list[NormalizedMetricsSnapshot] = []

        for run in runs_data:
            if not isinstance(run, dict):
                continue
            run_id = str(run.get("run_id") or run.get("experiment_id", "N/A"))
            ts = str(run.get("timestamp") or run.get("started_at", "N/A"))
            m_summary = (
                run.get("metrics_summary") if isinstance(run.get("metrics_summary"), dict) else {}
            )

            norm_items: list[NormalizedMetricItem] = []
            score_acc = 0.0
            weight_sum = 0.0

            for m_key, lower_is_better in metric_directions.items():
                if m_key not in bounds:
                    continue

                min_v, max_v = bounds[m_key]
                raw_v = run.get(m_key) or (
                    m_summary.get(m_key) if isinstance(m_summary, dict) else None
                )
                if raw_v is None:
                    continue

                raw_v = float(raw_v)
                n_v = cls.normalize_single_value(raw_v, min_v, max_v, lower_is_better)

                norm_items.append(
                    NormalizedMetricItem(
                        metric_name=m_key,
                        raw_value=raw_v,
                        normalized_value=n_v,
                        lower_is_better=lower_is_better,
                        unit=metric_units.get(m_key, ""),
                    )
                )

                if m_key in w:
                    score_acc += n_v * w[m_key]
                    weight_sum += w[m_key]

            composite = round((score_acc / max(0.001, weight_sum)) * 100.0, 2)

            snap = NormalizedMetricsSnapshot(
                run_id=run_id,
                timestamp=ts,
                normalized_metrics=norm_items,
                composite_score=composite,
            )

            # Persist normalized snapshot manifest
            out_file = out_dir / f"{run_id}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(snap.model_dump_json(indent=2))

            snapshots.append(snap)

        logger.info("Normalized benchmark metrics dataset", runs_count=len(snapshots))
        return snapshots
