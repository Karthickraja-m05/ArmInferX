"""ArmServe Cost Calculation Engine.

Calculates granular cloud infrastructure costs (cost per request, cost per token, cost per 1M tokens,
cost per hour, cost per benchmark run) using configurable provider pricing models.
"""

import time
from pathlib import Path

import structlog
from pydantic import BaseModel, Field

from backend.app.services.cost_resource_collector import ResourceUsageMeasurement

logger = structlog.get_logger("backend.app.services.cost_calculator")

CALCULATIONS_DIR = Path("storage/cost/calculations")


class ProviderPricingConfig(BaseModel):
    provider: str = "aws"
    instance_type: str = "c7g.xlarge"
    hourly_rate_usd: float = Field(default=0.1450, ge=0.0001)
    pricing_model: str = "on_demand"  # on_demand | spot | reserved
    region: str = "us-east-1"
    architecture: str = "arm64"


class CostEstimate(BaseModel):
    calculation_id: str
    measurement_id: str
    config_id: str
    experiment_id: str
    timestamp: str
    pricing: ProviderPricingConfig
    cost_per_benchmark_run: float
    cost_per_minute: float
    cost_per_hour: float
    cost_per_request: float
    cost_per_token: float
    cost_per_million_tokens: float
    throughput_per_dollar: float
    tokens_per_dollar: float
    assumptions: list[str]


class CostCalculator:
    """Production Cost Calculation Engine with Configurable Cloud Pricing."""

    def __init__(self, target_dir: Path | None = None) -> None:
        self.target_dir = target_dir or CALCULATIONS_DIR
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def calculate_cost(
        self,
        measurement: ResourceUsageMeasurement,
        pricing: ProviderPricingConfig | None = None,
    ) -> CostEstimate:
        """Calculate complete cost metrics for a resource usage measurement."""
        p = pricing or ProviderPricingConfig()
        calc_id = f"ccalc-{int(time.time())}"
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Calculations
        cost_per_sec = p.hourly_rate_usd / 3600.0
        cost_per_min = p.hourly_rate_usd / 60.0
        cost_per_hour = p.hourly_rate_usd

        run_cost = cost_per_sec * measurement.execution_duration_sec

        cost_per_req = run_cost / max(1, measurement.total_requests_processed)
        cost_per_tok = run_cost / max(1, measurement.total_tokens_generated)
        cost_per_1m_tok = cost_per_tok * 1_000_000.0

        tpd = measurement.requests_per_second / max(0.0001, p.hourly_rate_usd)
        tkpd = measurement.tokens_per_second / max(0.0001, p.hourly_rate_usd)

        assumptions = [
            f"Provider pricing based on {p.provider.upper()} {p.instance_type} ({p.pricing_model}) at ${p.hourly_rate_usd:.4f}/hr.",
            f"Execution duration of {measurement.execution_duration_sec:.2f}s processed {measurement.total_requests_processed} requests.",
            f"Generated {measurement.total_tokens_generated} tokens under concurrency level {measurement.concurrency_level}.",
        ]

        estimate = CostEstimate(
            calculation_id=calc_id,
            measurement_id=measurement.measurement_id,
            config_id=measurement.config_id,
            experiment_id=measurement.experiment_id,
            timestamp=now_str,
            pricing=p,
            cost_per_benchmark_run=round(run_cost, 6),
            cost_per_minute=round(cost_per_min, 6),
            cost_per_hour=round(cost_per_hour, 6),
            cost_per_request=round(cost_per_req, 8),
            cost_per_token=round(cost_per_tok, 10),
            cost_per_million_tokens=round(cost_per_1m_tok, 4),
            throughput_per_dollar=round(tpd, 2),
            tokens_per_dollar=round(tkpd, 2),
            assumptions=assumptions,
        )

        out_file = self.target_dir / f"{calc_id}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(estimate.model_dump_json(indent=2))

        logger.info(
            "Completed cost calculation",
            calc_id=calc_id,
            run_cost=run_cost,
            cost_1m=cost_per_1m_tok,
        )
        return estimate
