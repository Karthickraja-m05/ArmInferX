"""ArmServe Autonomous Agent Planning Engine.

Generates structured experiment proposals and hypotheses based on observed benchmark history,
quality evaluations, and cost models while preventing duplicate trials.
"""

import hashlib
import json
from pathlib import Path
import time
from typing import Any, Literal

import structlog
from pydantic import BaseModel, Field

from backend.app.services.agent_observation_engine import AgentStateSnapshot

logger = structlog.get_logger("backend.app.services.agent_planning_engine")

PLANS_DIR = Path("storage/agent/plans")


class ExperimentProposal(BaseModel):
    proposal_id: str
    target_model_id: str
    configuration: dict[str, Any]
    objective: str
    expected_improvement_hypothesis: str
    strategy: Literal["EXPLORE_UNEXPLORED", "REFINE_PROMISING", "AVOID_FAILURE"]
    hash_signature: str


class OptimizationPlan(BaseModel):
    plan_id: str
    snapshot_id: str
    timestamp: str
    proposals: list[ExperimentProposal]
    rationale: str


class AgentPlanningEngine:
    """Production Experiment Planning Engine for Autonomous Optimization Agent."""

    def __init__(self, target_dir: Path | None = None) -> None:
        self.target_dir = target_dir or PLANS_DIR
        self.target_dir.mkdir(parents=True, exist_ok=True)
        self.hashes_dir = self.target_dir / ".hashes"
        self.hashes_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def compute_config_hash(config: dict[str, Any]) -> str:
        """Compute deterministic hash of configuration parameter combination."""
        canonical = f"t={config.get('thread_count')}|b={config.get('batch_size')}|q={config.get('quantization_variant')}"
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]

    def _is_duplicate(self, config_hash: str) -> bool:
        """Check if configuration hash has already been planned or executed."""
        self.hashes_dir.mkdir(parents=True, exist_ok=True)
        hash_file = self.hashes_dir / f"{config_hash}.hash"
        return hash_file.exists()

    def _mark_hash(self, config_hash: str) -> None:
        """Mark configuration hash as planned to prevent duplicate creation."""
        self.hashes_dir.mkdir(parents=True, exist_ok=True)
        hash_file = self.hashes_dir / f"{config_hash}.hash"
        hash_file.touch(exist_ok=True)

    def create_plan(
        self,
        snapshot: AgentStateSnapshot,
        target_model_id: str = "qwen2.5-0.5b-instruct",
    ) -> OptimizationPlan:
        """Generate structured experiment plan based on state snapshot telemetry."""
        self.target_dir.mkdir(parents=True, exist_ok=True)
        self.hashes_dir.mkdir(parents=True, exist_ok=True)

        plan_id = f"plan-{int(time.time())}"
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ")

        proposals: list[ExperimentProposal] = []
        c_cfg = snapshot.runtime_configuration

        # Candidate 1: Refine promising thread count
        cand1_threads = 4 if c_cfg.get("thread_count", 4) != 4 else 8
        c1 = {
            "model_id": target_model_id,
            "thread_count": cand1_threads,
            "batch_size": c_cfg.get("batch_size", 64),
            "context_length": c_cfg.get("context_length", 2048),
            "temperature": c_cfg.get("temperature", 0.7),
            "max_tokens": c_cfg.get("max_tokens", 128),
            "quantization_variant": c_cfg.get("quantization_variant", "Q4_K_M"),
        }
        h1 = self.compute_config_hash(c1)
        if not self._is_duplicate(h1):
            self._mark_hash(h1)
            proposals.append(
                ExperimentProposal(
                    proposal_id=f"prop-{h1}",
                    target_model_id=target_model_id,
                    configuration=c1,
                    objective="Refine vCPU Thread Core Scaling",
                    expected_improvement_hypothesis=f"Increasing threads to {cand1_threads} improves matrix token generation throughput on Graviton ARM64.",
                    strategy="REFINE_PROMISING",
                    hash_signature=h1,
                )
            )

        # Candidate 2: Explore high-batch throughput
        cand2_batch = 128 if c_cfg.get("batch_size", 64) != 128 else 32
        c2 = {
            "model_id": target_model_id,
            "thread_count": 4,
            "batch_size": cand2_batch,
            "context_length": c_cfg.get("context_length", 2048),
            "temperature": c_cfg.get("temperature", 0.7),
            "max_tokens": c_cfg.get("max_tokens", 128),
            "quantization_variant": "Q4_K_M",
        }
        h2 = self.compute_config_hash(c2)
        if not self._is_duplicate(h2):
            self._mark_hash(h2)
            proposals.append(
                ExperimentProposal(
                    proposal_id=f"prop-{h2}",
                    target_model_id=target_model_id,
                    configuration=c2,
                    objective="Explore High-Throughput Batch Processing",
                    expected_improvement_hypothesis=f"Scaling batch size to {cand2_batch} increases RPS and reduces cost per 1M tokens.",
                    strategy="EXPLORE_UNEXPLORED",
                    hash_signature=h2,
                )
            )

        # Fallback if candidates were already evaluated
        if not proposals:
            c_fb = {
                "model_id": target_model_id,
                "thread_count": 2,
                "batch_size": 16,
                "context_length": 2048,
                "temperature": 0.5,
                "max_tokens": 128,
                "quantization_variant": "Q4_K_M",
            }
            h_fb = self.compute_config_hash(c_fb)
            proposals.append(
                ExperimentProposal(
                    proposal_id=f"prop-{h_fb}",
                    target_model_id=target_model_id,
                    configuration=c_fb,
                    objective="Fallback Exploration Trial",
                    expected_improvement_hypothesis="Evaluate lightweight thread and batch allocation under memory constraints.",
                    strategy="EXPLORE_UNEXPLORED",
                    hash_signature=h_fb,
                )
            )

        plan = OptimizationPlan(
            plan_id=plan_id,
            snapshot_id=snapshot.snapshot_id,
            timestamp=now_str,
            proposals=proposals,
            rationale=f"Generated {len(proposals)} non-duplicate experiment proposals derived from state snapshot '{snapshot.snapshot_id}'.",
        )

        out_file = self.target_dir / f"{plan_id}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(plan.model_dump_json(indent=2))

        logger.info("Generated optimization plan", plan_id=plan_id, count=len(proposals))
        return plan
