"""ArmServe Autonomous Agent Decision Engine.

Evaluates current optimization snapshot telemetry against action rules and stopping criteria
(STOP_CONVERGED, STOP_MAX_EXPERIMENTS, EXECUTE_PLAN) with evidence-based reasoning.
"""

import json
from pathlib import Path
import time
from typing import Any, Literal

import structlog
from pydantic import BaseModel, Field

from backend.app.services.agent_observation_engine import AgentStateSnapshot
from backend.app.services.agent_planning_engine import OptimizationPlan

logger = structlog.get_logger("backend.app.services.agent_decision_engine")

DECISIONS_DIR = Path("storage/agent/decisions")


class ActionDecision(BaseModel):
    decision_id: str
    snapshot_id: str
    plan_id: str | None = None
    timestamp: str
    action_type: Literal["EXECUTE_PLAN", "STOP_CONVERGED", "STOP_MAX_EXPERIMENTS", "STOP_SAFETY_GUARDRAIL"]
    chosen_proposal_id: str | None = None
    target_configuration: dict[str, Any] | None = None
    reasoning: str
    stopping_criteria_triggered: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def action(self) -> str:
        return self.action_type

    @property
    def target_proposal_id(self) -> str | None:
        return self.chosen_proposal_id

    @property
    def explanation(self) -> str:
        return self.reasoning


AgentDecision = ActionDecision


class AgentDecisionEngine:
    """Production Action & Stopping Criteria Decision Engine for Autonomous Optimization Agent."""

    def __init__(
        self,
        target_dir: Path | None = None,
        max_total_experiments: int = 10,
        min_quality_threshold: float = 80.0,
        convergence_score_threshold: float = 98.0,
        plateau_delta_threshold: float = 0.5,
    ) -> None:
        self.target_dir = target_dir or DECISIONS_DIR
        self.target_dir.mkdir(parents=True, exist_ok=True)
        self.max_total_experiments = max_total_experiments
        self.min_quality_threshold = min_quality_threshold
        self.convergence_score_threshold = convergence_score_threshold
        self.plateau_delta_threshold = plateau_delta_threshold

    def evaluate_decision(
        self,
        snapshot: AgentStateSnapshot,
        plan: OptimizationPlan | None = None,
        composite_utility_score: float | None = None,
        current_step: int | None = None,
        max_steps: int | None = None,
        historical_scores: list[float] | None = None,
    ) -> ActionDecision:
        """Evaluate action rules and stopping criteria based on current observation snapshot."""
        decision_id = f"dec-{int(time.time())}"
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Stopping Rule 1: Step budget or Total Experiment Budget Reached
        effective_max = max_steps or self.max_total_experiments
        if (current_step and current_step > effective_max) or (
            snapshot.total_experiments_recorded >= self.max_total_experiments
        ):
            dec = ActionDecision(
                decision_id=decision_id,
                snapshot_id=snapshot.snapshot_id,
                plan_id=plan.plan_id if plan else None,
                timestamp=now_str,
                action_type="STOP_MAX_EXPERIMENTS",
                reasoning=f"Reached maximum allocated experiment budget ({current_step or snapshot.total_experiments_recorded}/{effective_max}). Stopping workflow.",
                stopping_criteria_triggered="STOP_MAX_EXPERIMENTS",
            )
            self._save_decision(dec)
            return dec

        # Stopping Rule 2: Score Plateau (Delta < threshold over recent trials)
        if historical_scores and len(historical_scores) >= 3:
            delta = max(historical_scores) - min(historical_scores)
            if delta < self.plateau_delta_threshold:
                dec = ActionDecision(
                    decision_id=decision_id,
                    snapshot_id=snapshot.snapshot_id,
                    plan_id=plan.plan_id if plan else None,
                    timestamp=now_str,
                    action_type="STOP_CONVERGED",
                    reasoning=f"Optimization scores plateaued with delta {delta:.2f} < {self.plateau_delta_threshold:.2f} across recent trials. Workflow converged.",
                    stopping_criteria_triggered="STOP_CONVERGED",
                )
                self._save_decision(dec)
                return dec

        # Stopping Rule 3: Optimization Target Converged
        if composite_utility_score and composite_utility_score >= self.convergence_score_threshold:
            dec = ActionDecision(
                decision_id=decision_id,
                snapshot_id=snapshot.snapshot_id,
                plan_id=plan.plan_id if plan else None,
                timestamp=now_str,
                action_type="STOP_CONVERGED",
                reasoning=f"Composite utility score {composite_utility_score:.2f} met or exceeded convergence threshold {self.convergence_score_threshold:.2f}. Optimal configuration achieved.",
                stopping_criteria_triggered="STOP_CONVERGED",
            )
            self._save_decision(dec)
            return dec

        # Stopping Rule 4: Quality Regression Safety Guardrail
        if snapshot.latest_quality_score and snapshot.latest_quality_score < self.min_quality_threshold:
            dec = ActionDecision(
                decision_id=decision_id,
                snapshot_id=snapshot.snapshot_id,
                plan_id=plan.plan_id if plan else None,
                timestamp=now_str,
                action_type="STOP_SAFETY_GUARDRAIL",
                reasoning=f"Quality score {snapshot.latest_quality_score:.1f}% dropped below mandatory SLA threshold {self.min_quality_threshold:.1f}%. Stopping autonomous exploration.",
                stopping_criteria_triggered="STOP_SAFETY_GUARDRAIL",
            )
            self._save_decision(dec)
            return dec

        # Action Rule 5: Execute Next Available Proposal
        if plan and plan.proposals:
            chosen = plan.proposals[0]
            dec = ActionDecision(
                decision_id=decision_id,
                snapshot_id=snapshot.snapshot_id,
                plan_id=plan.plan_id,
                timestamp=now_str,
                action_type="EXECUTE_PLAN",
                chosen_proposal_id=chosen.proposal_id,
                target_configuration=chosen.configuration,
                reasoning=f"Selected top proposal '{chosen.proposal_id}' ({chosen.objective}) under strategy '{chosen.strategy}'.",
            )
            self._save_decision(dec)
            return dec

        # Action Rule 6: Stop if no proposals remain
        dec = ActionDecision(
            decision_id=decision_id,
            snapshot_id=snapshot.snapshot_id,
            plan_id=plan.plan_id if plan else None,
            timestamp=now_str,
            action_type="STOP_CONVERGED",
            reasoning="No non-duplicate proposals remaining in plan. Workflow converged.",
            stopping_criteria_triggered="STOP_CONVERGED",
        )
        self._save_decision(dec)
        return dec

    def _save_decision(self, decision: ActionDecision) -> None:
        """Persist decision record to disk."""
        self.target_dir.mkdir(parents=True, exist_ok=True)
        out_file = self.target_dir / f"{decision.decision_id}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(decision.model_dump_json(indent=2))
        logger.info("Persisted agent action decision", decision_id=decision.decision_id, action=decision.action_type)
