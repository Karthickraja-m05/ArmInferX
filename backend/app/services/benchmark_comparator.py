"""ArmServe Benchmark Run Comparison & Regression Detection Engine."""

import json
from typing import Any

from pydantic import BaseModel

from backend.app.services.benchmark_runner import BENCHMARKS_DIR


class MetricComparison(BaseModel):
    metric_name: str
    unit: str
    run_a_value: float
    run_b_value: float
    absolute_difference: float
    percentage_difference: float
    direction: str  # IMPROVED, REGRESSED, UNCHANGED
    is_regression: bool


class BenchmarkComparisonReport(BaseModel):
    run_a_id: str
    run_b_id: str
    run_a_timestamp: str
    run_b_timestamp: str
    verdict: str  # IMPROVED, REGRESSED, NEUTRAL
    comparisons: list[MetricComparison]
    summary_notes: list[str]


class BenchmarkComparator:
    """Production Comparator for Evaluating Performance Variations Between Benchmark Runs."""

    @staticmethod
    def load_run_manifest(run_id: str) -> dict[str, Any]:
        """Load benchmark run manifest by ID from storage or database."""
        # Try direct path first
        file_path = BENCHMARKS_DIR / f"{run_id}.json"
        if not file_path.exists():
            # Search by prefix/filename
            matches = list(BENCHMARKS_DIR.glob(f"*{run_id}*.json"))
            if not matches:
                raise ValueError(f"Benchmark run '{run_id}' not found.")
            file_path = matches[0]

        with open(file_path, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
            return data

    @classmethod
    def compare_runs(cls, run_a_id: str, run_b_id: str) -> BenchmarkComparisonReport:
        """Perform quantitative comparison between Run A (Baseline) and Run B (Candidate)."""
        data_a = cls.load_run_manifest(run_a_id)
        data_b = cls.load_run_manifest(run_b_id)

        comparisons: list[MetricComparison] = []
        summary_notes: list[str] = []
        regressions_count = 0
        improvements_count = 0

        def eval_metric(
            name: str,
            unit: str,
            val_a: float,
            val_b: float,
            lower_is_better: bool = True,
            threshold_pct: float = 5.0,
        ) -> MetricComparison:
            nonlocal regressions_count, improvements_count
            abs_diff = round(val_b - val_a, 2)
            pct_diff = round(((val_b - val_a) / max(0.0001, val_a)) * 100.0, 2)

            is_reg = False
            direction = "UNCHANGED"

            if abs(pct_diff) < 1.0:
                direction = "UNCHANGED"
            elif lower_is_better:
                if pct_diff > threshold_pct:
                    direction = "REGRESSED"
                    is_reg = True
                    regressions_count += 1
                elif pct_diff < -1.0:
                    direction = "IMPROVED"
                    improvements_count += 1
                else:
                    direction = "UNCHANGED"
            else:  # Higher is better (e.g. RPS, TPS)
                if pct_diff < -threshold_pct:
                    direction = "REGRESSED"
                    is_reg = True
                    regressions_count += 1
                elif pct_diff > 1.0:
                    direction = "IMPROVED"
                    improvements_count += 1
                else:
                    direction = "UNCHANGED"

            return MetricComparison(
                metric_name=name,
                unit=unit,
                run_a_value=round(val_a, 2),
                run_b_value=round(val_b, 2),
                absolute_difference=abs_diff,
                percentage_difference=pct_diff,
                direction=direction,
                is_regression=is_reg,
            )

        # Evaluate Latencies (Lower is better)
        comparisons.append(
            eval_metric(
                "P50 Latency",
                "ms",
                data_a.get("latency_p50_ms", 0),
                data_b.get("latency_p50_ms", 0),
                lower_is_better=True,
            )
        )
        comparisons.append(
            eval_metric(
                "P90 Latency",
                "ms",
                data_a.get("latency_p90_ms", 0),
                data_b.get("latency_p90_ms", 0),
                lower_is_better=True,
            )
        )
        comparisons.append(
            eval_metric(
                "P99 Latency",
                "ms",
                data_a.get("latency_p99_ms", 0),
                data_b.get("latency_p99_ms", 0),
                lower_is_better=True,
            )
        )

        # Evaluate Throughput (Higher is better)
        comparisons.append(
            eval_metric(
                "Requests Per Second",
                "req/s",
                data_a.get("requests_per_second", 0),
                data_b.get("requests_per_second", 0),
                lower_is_better=False,
            )
        )
        comparisons.append(
            eval_metric(
                "Tokens Per Second",
                "tok/s",
                data_a.get("tokens_per_second", 0),
                data_b.get("tokens_per_second", 0),
                lower_is_better=False,
            )
        )

        # Evaluate Memory Usage (Lower is better)
        comparisons.append(
            eval_metric(
                "Peak Memory",
                "MB",
                data_a.get("peak_memory_mb", 0),
                data_b.get("peak_memory_mb", 0),
                lower_is_better=True,
            )
        )

        # Determine overall verdict
        if regressions_count > 0:
            verdict = "REGRESSED"
            summary_notes.append(
                f"Detected {regressions_count} performance regression(s) exceeding {5.0}% threshold."
            )
        elif improvements_count > 0:
            verdict = "IMPROVED"
            summary_notes.append(
                f"Measured {improvements_count} performance improvement(s) in candidate run B."
            )
        else:
            verdict = "NEUTRAL"
            summary_notes.append(
                "No statistically significant performance variation detected between runs."
            )

        return BenchmarkComparisonReport(
            run_a_id=data_a.get("run_id", run_a_id),
            run_b_id=data_b.get("run_id", run_b_id),
            run_a_timestamp=data_a.get("timestamp", "N/A"),
            run_b_timestamp=data_b.get("timestamp", "N/A"),
            verdict=verdict,
            comparisons=comparisons,
            summary_notes=summary_notes,
        )
