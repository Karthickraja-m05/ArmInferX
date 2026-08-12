"""ArmServe Autonomous Optimization Workflow Orchestrator.

Executes end-to-end autonomous optimization cycles (Observation -> Planning -> Decision ->
Execution -> Benchmarking -> Quality Evaluation -> Cost Analysis -> Scoring -> Recommendation).
"""

import json
from pathlib import Path
import time
from typing import Any

import structlog
from pydantic import BaseModel, Field

from backend.app.services.agent_decision_engine import AgentDecision, AgentDecisionEngine
from backend.app.services.agent_observation_engine import AgentObservationEngine, AgentStateSnapshot
from backend.app.services.agent_planning_engine import AgentPlanningEngine, OptimizationPlan
from backend.app.services.benchmark_runner import BenchmarkRunner
from backend.app.services.configuration_ranker import ConfigurationRanker
from backend.app.services.constraint_engine import ConstraintEngine
from backend.app.services.cost_calculator import CostCalculator
from backend.app.services.cost_resource_collector import CostResourceCollector
from backend.app.services.experiment_executor import ExperimentExecutor
from backend.app.services.metrics_normalizer import MetricsNormalizer
from backend.app.services.quality_response_collector import QualityResponseCollector
from backend.app.services.quality_scoring_engine import QualityScoringEngine
from backend.app.services.recommendation_engine import RecommendationEngine
from backend.app.services.scoring_engine import ScoringEngine

logger = structlog.get_logger("backend.app.services.agent_workflow_orchestrator")

WORKFLOWS_DIR = Path("storage/agent/workflows")


class WorkflowStepRecord(BaseModel):
    step_number: int
    snapshot: AgentStateSnapshot
    plan: OptimizationPlan
    decision: AgentDecision
    experiment_id: str | None = None
    benchmark_id: str | None = None
    quality_score: float | None = None
    cost_per_1m_tokens: float | None = None
    composite_utility_score: float | None = None


class WorkflowExecutionRecord(BaseModel):
    workflow_id: str
    target_model_id: str
    timestamp: str
    status: str = "COMPLETED"
    total_steps_executed: int
    stopping_reason: str
    best_config_id: str | None = None
    best_utility_score: float | None = None
    steps: list[WorkflowStepRecord]


class AgentWorkflowOrchestrator:
    """Production Closed-Loop Autonomous Optimization Workflow Orchestrator."""

    def __init__(self, target_dir: Path | None = None) -> None:
        self.target_dir = target_dir or WORKFLOWS_DIR
        self.target_dir.mkdir(parents=True, exist_ok=True)
        self.observer = AgentObservationEngine()
        self.planner = AgentPlanningEngine()
        self.decision_engine = AgentDecisionEngine()
        self.executor = ExperimentExecutor()
        self.benchmarker = BenchmarkRunner()
        self.cost_collector = CostResourceCollector()
        self.cost_calculator = CostCalculator()
        self.quality_collector = QualityResponseCollector()
        self.quality_scorer = QualityScoringEngine()
        self.normalizer = MetricsNormalizer()
        self.scoring_engine = ScoringEngine()
        self.constraint_engine = ConstraintEngine()
        self.ranker = ConfigurationRanker()
        self.recommender = RecommendationEngine()

    async def run_autonomous_optimization_loop(
        self,
        target_model_id: str = "qwen2.5-0.5b-instruct",
        max_steps: int = 3,
    ) -> WorkflowExecutionRecord:
        """Run full autonomous optimization loop through all required intermediate steps."""
        wf_id = f"wf-{int(time.time())}"
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ")

        step_records: list[WorkflowStepRecord] = []
        historical_scores: list[float] = []

        stopping_reason = "Optimization completed normally."
        best_cfg_id: str | None = None
        best_score: float | None = None

        logger.info("Starting autonomous optimization workflow", workflow_id=wf_id, target_model_id=target_model_id, max_steps=max_steps)

        for step_idx in range(1, max_steps + 1):
            # 1. Observe state
            snapshot = self.observer.capture_state_snapshot(
                active_model_id=target_model_id,
                top_ranked_config_id=best_cfg_id,
                latest_quality_score=step_records[-1].quality_score if step_records else None,
                latest_cost_per_1m_tokens=step_records[-1].cost_per_1m_tokens if step_records else None,
            )

            # 2. Generate plan
            plan = self.planner.create_plan(snapshot, target_model_id=target_model_id)

            # 3. Evaluate decision
            decision = self.decision_engine.evaluate_decision(
                snapshot=snapshot,
                plan=plan,
                current_step=step_idx,
                max_steps=max_steps,
                historical_scores=historical_scores,
            )

            # Check stopping action
            if decision.action.startswith("STOP"):
                stopping_reason = decision.explanation
                step_records.append(
                    WorkflowStepRecord(
                        step_number=step_idx,
                        snapshot=snapshot,
                        plan=plan,
                        decision=decision,
                    )
                )
                break

            # 4. Intermediate Steps: Execute experiment & benchmark
            target_config = decision.target_configuration or {
                "model_id": target_model_id,
                "thread_count": 4,
                "batch_size": 64,
                "context_length": 2048,
                "temperature": 0.7,
                "max_tokens": 128,
                "quantization_variant": "Q4_K_M",
            }

            exp_result = await self.executor.execute_experiment(
                config=target_config,
                runtime_version="1.0.0-arm64",
            )

            bench_result = exp_result.get("benchmark_result", {})
            metrics_summary = bench_result.get("metrics_summary", {})

            # 5. Cost Analysis
            dur_sec = metrics_summary.get("total_duration_sec", 2.0)
            rps = metrics_summary.get("requests_per_second", 50.0)
            tps = metrics_summary.get("tokens_per_second", 1000.0)
            tot_req = int(rps * dur_sec)
            tot_tok = int(tps * dur_sec)

            m_cost = self.cost_collector.record_resource_usage(
                benchmark_id=bench_result.get("benchmark_id", f"bench-{step_idx}"),
                experiment_id=exp_result.get("experiment_id", f"exp-{step_idx}"),
                config_id=target_config.get("config_id", f"cfg-{step_idx}"),
                cpu_utilization_pct=metrics_summary.get("cpu_utilization_pct", 40.0),
                peak_memory_mb=metrics_summary.get("peak_memory_mb", 350.0),
                average_memory_mb=metrics_summary.get("average_memory_mb", 320.0),
                execution_duration_sec=dur_sec,
                total_requests_processed=max(1, tot_req),
                total_tokens_generated=max(1, tot_tok),
                concurrency_level=target_config.get("batch_size", 1),
            )
            c_est = self.cost_calculator.calculate_cost(m_cost)

            # 6. Quality Evaluation
            q_coll = await self.quality_collector.collect_dataset_responses(
                config_id=target_config.get("config_id", f"cfg-{step_idx}"),
                experiment_id=exp_result.get("experiment_id", f"exp-{step_idx}"),
            )
            q_eval = self.quality_scorer.evaluate_collection_record(q_coll)

            # 7. Normalize & Score
            # Dummy run wrap for scoring pipeline
            run_item = {
                "config_id": target_config.get("config_id", f"cfg-{step_idx}"),
                "experiment_id": exp_result.get("experiment_id", f"exp-{step_idx}"),
                "metrics_summary": metrics_summary,
            }
            norm_runs = self.normalizer.normalize_benchmark_runs([run_item])
            score_item = self.scoring_engine.compute_experiment_score(norm_runs[0])
            u_score = getattr(score_item, "total_score", getattr(score_item, "total_utility_score", score_item.get("total_score", 0.0) if isinstance(score_item, dict) else 0.0))

            historical_scores.append(u_score)
            if best_score is None or u_score > best_score:
                best_score = u_score
                best_cfg_id = target_config.get("config_id", f"cfg-{step_idx}")

            step_records.append(
                WorkflowStepRecord(
                    step_number=step_idx,
                    snapshot=snapshot,
                    plan=plan,
                    decision=decision,
                    experiment_id=exp_result.get("experiment_id"),
                    benchmark_id=bench_result.get("benchmark_id"),
                    quality_score=q_eval.overall_quality_score,
                    cost_per_1m_tokens=c_est.cost_per_million_tokens,
                    composite_utility_score=u_score,
                )
            )

        wf_record = WorkflowExecutionRecord(
            workflow_id=wf_id,
            target_model_id=target_model_id,
            timestamp=now_str,
            status="COMPLETED",
            total_steps_executed=len(step_records),
            stopping_reason=stopping_reason,
            best_config_id=best_cfg_id,
            best_utility_score=best_score,
            steps=step_records,
        )

        out_file = self.target_dir / f"{wf_id}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(wf_record.model_dump_json(indent=2))

        logger.info(
            "Autonomous optimization workflow completed",
            workflow_id=wf_id,
            steps=len(step_records),
            best_score=best_score,
        )
        return wf_record
