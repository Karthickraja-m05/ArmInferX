"""ArmServe Cost Comparison Engine.

Compares cost estimates between Configuration A and Configuration B, computes absolute savings,
percentage cost reductions, throughput per dollar efficiency, and persists ranked comparisons.
"""

import json
from pathlib import Path
import time
from typing import Any

import structlog
from pydantic import BaseModel, Field

from backend.app.services.cost_calculator import CostEstimate

logger = structlog.get_logger("backend.app.services.cost_comparator")

COMPARISONS_DIR = Path("storage/cost/comparisons")


class CostComparisonReport(BaseModel):
    comparison_id: str
    baseline_calc_id: str
    target_calc_id: str
    baseline_config_id: str
    target_config_id: str
    timestamp: str
    baseline_cost_1m_tokens: float
    target_cost_1m_tokens: float
    absolute_cost_difference_1m: float
    percentage_cost_savings: float
    baseline_tokens_per_dollar: float
    target_tokens_per_dollar: float
    tokens_per_dollar_gain_pct: float
    more_cost_effective: bool
    summary_reasoning: str


class CostComparator:
    """Production Cost Comparison Engine."""

    def __init__(self, target_dir: Path | None = None) -> None:
        self.target_dir = target_dir or COMPARISONS_DIR
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def compare_estimates(
        self,
        baseline: CostEstimate,
        target: CostEstimate,
    ) -> CostComparisonReport:
        """Compare baseline cost estimate against target cost estimate."""
        comp_id = f"ccomp-{int(time.time())}"
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ")

        b_c1m = baseline.cost_per_million_tokens
        t_c1m = target.cost_per_million_tokens

        abs_diff = round(t_c1m - b_c1m, 4)
        pct_savings = round(((b_c1m - t_c1m) / max(0.0001, b_c1m)) * 100.0, 2)

        b_tkpd = baseline.tokens_per_dollar
        t_tkpd = target.tokens_per_dollar
        tkpd_gain_pct = round(((t_tkpd - b_tkpd) / max(0.0001, b_tkpd)) * 100.0, 2)

        more_effective = t_c1m < b_c1m

        if more_effective:
            reason = (
                f"Configuration '{target.config_id}' reduces cost per 1M tokens by ${abs(abs_diff):.4f} "
                f"({pct_savings:.1f}% savings) while increasing efficiency to {t_tkpd:,.0f} tokens/dollar (+{tkpd_gain_pct:.1f}%)."
            )
        elif t_c1m > b_c1m:
            reason = (
                f"Configuration '{target.config_id}' increases cost per 1M tokens by +${abs_diff:.4f} "
                f"(+{abs(pct_savings):.1f}% expense) compared to baseline."
            )
        else:
            reason = f"Configuration '{target.config_id}' has identical cost efficiency to baseline."

        report = CostComparisonReport(
            comparison_id=comp_id,
            baseline_calc_id=baseline.calculation_id,
            target_calc_id=target.calculation_id,
            baseline_config_id=baseline.config_id,
            target_config_id=target.config_id,
            timestamp=now_str,
            baseline_cost_1m_tokens=b_c1m,
            target_cost_1m_tokens=t_c1m,
            absolute_cost_difference_1m=abs_diff,
            percentage_cost_savings=pct_savings,
            baseline_tokens_per_dollar=b_tkpd,
            target_tokens_per_dollar=t_tkpd,
            tokens_per_dollar_gain_pct=tkpd_gain_pct,
            more_cost_effective=more_effective,
            summary_reasoning=reason,
        )

        out_file = self.target_dir / f"{comp_id}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))

        logger.info("Completed cost comparison", comp_id=comp_id, savings_pct=pct_savings, effective=more_effective)
        return report

    def rank_configurations_by_cost(self, estimates: list[CostEstimate]) -> list[CostEstimate]:
        """Rank configuration cost estimates by cost per 1M tokens (ascending)."""
        return sorted(estimates, key=lambda e: e.cost_per_million_tokens)
