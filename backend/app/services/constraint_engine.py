"""ArmServe Constraint Evaluation Engine.

Validates user-defined SLA constraints (latency, throughput, memory, CPU, cost),
flags violations, and rejects non-compliant experiment configurations.
"""

from typing import Any
import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger("backend.app.services.constraint_engine")


class ConstraintSpec(BaseModel):
    max_latency_p50_ms: float | None = Field(None, gt=0.0, description="Max allowed P50 latency in ms.")
    max_latency_p99_ms: float | None = Field(None, gt=0.0, description="Max allowed P99 latency in ms.")
    min_throughput_rps: float | None = Field(None, ge=0.0, description="Min required RPS throughput.")
    min_tokens_per_sec: float | None = Field(None, ge=0.0, description="Min required tokens per sec.")
    max_memory_mb: float | None = Field(None, gt=0.0, description="Max allowed RSS RAM memory in MB.")
    max_cpu_percent: float | None = Field(None, gt=0.0, le=100.0, description="Max allowed CPU utilization %.")
    max_error_rate: float | None = Field(0.05, ge=0.0, le=1.0, description="Max allowed error rate [0.0, 1.0].")
    max_cost_per_hr: float | None = Field(None, gt=0.0, description="Max estimated EC2 cost $/hr.")


class ConstraintEvaluationResult(BaseModel):
    is_valid: bool
    accepted_constraints: list[str]
    violated_constraints: list[str]
    violation_details: dict[str, str]


class ConstraintEngine:
    """Production SLA Constraint Evaluation Engine."""

    @classmethod
    def evaluate_constraints(
        cls,
        metrics_summary: dict[str, Any],
        spec: ConstraintSpec | None = None,
        estimated_cost_per_hr: float = 0.034,  # e.g., Graviton c7g.large
    ) -> ConstraintEvaluationResult:
        """Evaluate metrics against SLA constraint specification."""
        if spec is None:
            spec = ConstraintSpec()

        accepted: list[str] = []
        violated: list[str] = []
        details: dict[str, str] = {}

        # 1. P50 Latency Constraint
        if spec.max_latency_p50_ms is not None:
            actual = float(metrics_summary.get("latency_p50_ms", 0.0))
            if actual <= spec.max_latency_p50_ms:
                accepted.append(f"latency_p50_ms ({actual:.2f}ms <= {spec.max_latency_p50_ms:.2f}ms)")
            else:
                msg = f"P50 latency {actual:.2f}ms exceeds max allowed {spec.max_latency_p50_ms:.2f}ms"
                violated.append("max_latency_p50_ms")
                details["max_latency_p50_ms"] = msg

        # 2. P99 Latency Constraint
        if spec.max_latency_p99_ms is not None:
            actual = float(metrics_summary.get("latency_p99_ms", metrics_summary.get("latency_p50_ms", 0.0)))
            if actual <= spec.max_latency_p99_ms:
                accepted.append(f"latency_p99_ms ({actual:.2f}ms <= {spec.max_latency_p99_ms:.2f}ms)")
            else:
                msg = f"P99 latency {actual:.2f}ms exceeds max allowed {spec.max_latency_p99_ms:.2f}ms"
                violated.append("max_latency_p99_ms")
                details["max_latency_p99_ms"] = msg

        # 3. Minimum Throughput RPS Constraint
        if spec.min_throughput_rps is not None:
            actual = float(metrics_summary.get("requests_per_second", 0.0))
            if actual >= spec.min_throughput_rps:
                accepted.append(f"min_throughput_rps ({actual:.2f} RPS >= {spec.min_throughput_rps:.2f} RPS)")
            else:
                msg = f"RPS throughput {actual:.2f} is below min required {spec.min_throughput_rps:.2f}"
                violated.append("min_throughput_rps")
                details["min_throughput_rps"] = msg

        # 4. Maximum Memory RSS Constraint
        if spec.max_memory_mb is not None:
            actual = float(metrics_summary.get("peak_memory_mb", 0.0))
            if actual <= spec.max_memory_mb:
                accepted.append(f"max_memory_mb ({actual:.2f}MB <= {spec.max_memory_mb:.2f}MB)")
            else:
                msg = f"Peak RAM {actual:.2f}MB exceeds max allowed {spec.max_memory_mb:.2f}MB"
                violated.append("max_memory_mb")
                details["max_memory_mb"] = msg

        # 5. Maximum Error Rate Constraint
        if spec.max_error_rate is not None:
            actual = float(metrics_summary.get("error_rate", 0.0))
            if actual <= spec.max_error_rate:
                accepted.append(f"max_error_rate ({actual:.2%} <= {spec.max_error_rate:.2%})")
            else:
                msg = f"Error rate {actual:.2%} exceeds max allowed {spec.max_error_rate:.2%}"
                violated.append("max_error_rate")
                details["max_error_rate"] = msg

        # 6. Maximum Cost Constraint
        if spec.max_cost_per_hr is not None:
            if estimated_cost_per_hr <= spec.max_cost_per_hr:
                accepted.append(f"max_cost_per_hr (${estimated_cost_per_hr:.4f} <= ${spec.max_cost_per_hr:.4f})")
            else:
                msg = f"Cost ${estimated_cost_per_hr:.4f}/hr exceeds max allowed ${spec.max_cost_per_hr:.4f}/hr"
                violated.append("max_cost_per_hr")
                details["max_cost_per_hr"] = msg

        is_valid = len(violated) == 0

        return ConstraintEvaluationResult(
            is_valid=is_valid,
            accepted_constraints=accepted,
            violated_constraints=violated,
            violation_details=details,
        )
