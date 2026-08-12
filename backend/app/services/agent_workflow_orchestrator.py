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
    recommendation_id: str | None = None
    recommendation_narrative: str | None = None


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

        # Runtime Agent State
        self._is_running: bool = False
        self._current_step: int = 0
        self._max_steps: int = 0
        self._active_model: str = "qwen2.5-0.5b-instruct"
        self._stop_requested: bool = False
        self._active_workflow_id: str | None = None
        self._latest_workflow: WorkflowExecutionRecord | None = None

    def get_status(self) -> dict[str, Any]:
        """Return live agent execution state snapshot."""
        return {
            "status": "RUNNING" if self._is_running else "IDLE",
            "is_running": self._is_running,
            "active_workflow_id": self._active_workflow_id,
            "active_model": self._active_model,
            "current_step": self._current_step,
            "max_steps": self._max_steps,
            "stop_requested": self._stop_requested,
            "latest_workflow_id": self._latest_workflow.workflow_id if self._latest_workflow else None,
            "latest_best_score": self._latest_workflow.best_utility_score if self._latest_workflow else None,
        }

    def request_stop(self) -> dict[str, Any]:
        """Signal the running optimization agent to abort gracefully."""
        if not self._is_running:
            return {"status": "NOT_RUNNING", "message": "Optimization Agent is currently idle."}
        self._stop_requested = True
        logger.info("Stop signal sent to Autonomous Optimization Agent", workflow_id=self._active_workflow_id)
        return {
            "status": "STOP_REQUESTED",
            "workflow_id": self._active_workflow_id,
            "message": "Optimization Agent will stop after the current step.",
        }

    async def run_autonomous_optimization_loop(
        self,
        target_model_id: str = "qwen2.5-0.5b-instruct",
        max_steps: int = 3,
    ) -> WorkflowExecutionRecord:
        """Run full autonomous optimization loop through all required intermediate steps."""
        self.target_dir.mkdir(parents=True, exist_ok=True)
        wf_id = f"wf-{int(time.time())}"
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ")

        self._is_running = True
        self._stop_requested = False
        self._active_workflow_id = wf_id
        self._active_model = target_model_id
        self._max_steps = max_steps
        self._current_step = 0

        step_records: list[WorkflowStepRecord] = []
        historical_scores: list[float] = []

        stopping_reason = "Optimization completed normally."
        best_cfg_id: str | None = None
        best_score: float | None = None

        logger.info(
            "Starting autonomous optimization workflow",
            workflow_id=wf_id,
            target_model_id=target_model_id,
            max_steps=max_steps,
        )

        try:
            for step_idx in range(1, max_steps + 1):
                self._current_step = step_idx

                if self._stop_requested:
                    stopping_reason = "User requested manual abort."
                    logger.info("Autonomous agent stopped by user request", workflow_id=wf_id, step=step_idx)
                    break

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

                if isinstance(exp_result, dict):
                    exp_id = exp_result.get("experiment_id", f"exp-{step_idx}")
                    bench_result = exp_result.get("benchmark_result", {})
                    metrics_summary = bench_result.get("metrics_summary", {}) or exp_result.get("metrics_summary", {})
                    bench_id = bench_result.get("benchmark_id") or exp_result.get("benchmark_run_id", f"bench-{step_idx}")
                else:
                    exp_id = getattr(exp_result, "experiment_id", f"exp-{step_idx}")
                    metrics_summary = getattr(exp_result, "metrics_summary", {}) or {}
                    bench_id = getattr(exp_result, "benchmark_run_id", f"bench-{step_idx}")

                # 5. Cost Analysis
                dur_sec = float(metrics_summary.get("total_duration_sec", 2.0))
                rps = float(metrics_summary.get("requests_per_second", 50.0))
                tps = float(metrics_summary.get("tokens_per_second", 1000.0))
                tot_req = int(rps * dur_sec)
                tot_tok = int(tps * dur_sec)

                m_cost = self.cost_collector.record_resource_usage(
                    benchmark_id=bench_id,
                    experiment_id=exp_id,
                    config_id=target_config.get("config_id", f"cfg-{step_idx}"),
                    cpu_utilization_pct=float(metrics_summary.get("cpu_utilization_pct", 40.0)),
                    peak_memory_mb=float(metrics_summary.get("peak_memory_mb", 350.0)),
                    average_memory_mb=float(metrics_summary.get("average_memory_mb", 320.0)),
                    execution_duration_sec=dur_sec,
                    total_requests_processed=max(1, tot_req),
                    total_tokens_generated=max(1, tot_tok),
                    concurrency_level=target_config.get("batch_size", 1),
                )
                c_est = self.cost_calculator.calculate_cost(m_cost)

                # 6. Quality Evaluation
                q_coll = await self.quality_collector.collect_dataset_responses(
                    config_id=target_config.get("config_id", f"cfg-{step_idx}"),
                    experiment_id=exp_id,
                )
                q_eval = self.quality_scorer.evaluate_collection_record(q_coll)

                # 7. Normalize & Score
                run_item = {
                    "config_id": target_config.get("config_id", f"cfg-{step_idx}"),
                    "experiment_id": exp_id,
                    "metrics_summary": metrics_summary,
                }
                norm_runs = self.normalizer.normalize_benchmark_runs([run_item])
                score_item = self.scoring_engine.compute_experiment_score(norm_runs[0])
                u_score = getattr(
                    score_item,
                    "total_score",
                    getattr(
                        score_item,
                        "total_utility_score",
                        score_item.get("total_score", 0.0) if isinstance(score_item, dict) else 0.0,
                    ),
                )

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
                        experiment_id=exp_id,
                        benchmark_id=bench_id,
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

            # Generate explainable recommendation
            try:
                from backend.app.services.agent_recommendation_engine import AgentRecommendationEngine
                agent_rec_engine = AgentRecommendationEngine()
                rec_report = agent_rec_engine.generate_recommendation(wf_record)
                wf_record.recommendation_id = rec_report.recommendation_id
                wf_record.recommendation_narrative = rec_report.human_readable_narrative
            except Exception as e:
                logger.warning("Could not auto-generate recommendation report", error=str(e))

            # Persist record
            out_file = self.target_dir / f"{wf_id}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(wf_record.model_dump_json(indent=2))

            latest_file = self.target_dir / "latest.json"
            with open(latest_file, "w", encoding="utf-8") as f:
                f.write(wf_record.model_dump_json(indent=2))

            self._latest_workflow = wf_record

            logger.info(
                "Autonomous optimization workflow completed",
                workflow_id=wf_id,
                steps=len(step_records),
                best_score=best_score,
            )
            return wf_record

        finally:
            self._is_running = False
            self._stop_requested = False

    def get_workflow_by_id(self, workflow_id: str) -> WorkflowExecutionRecord | None:
        """Load workflow execution record from disk."""
        target_file = self.target_dir / f"{workflow_id}.json"
        if not target_file.exists():
            return None
        with open(target_file, "r", encoding="utf-8") as f:
            return WorkflowExecutionRecord.model_validate_json(f.read())

    def list_workflows(
        self,
        limit: int = 20,
        offset: int = 0,
        target_model_id: str | None = None,
    ) -> list[WorkflowExecutionRecord]:
        """List persisted workflow records with pagination and filtering."""
        files = [f for f in self.target_dir.glob("*.json") if f.name != "latest.json"]
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        results: list[WorkflowExecutionRecord] = []
        for file in files:
            try:
                with open(file, "r", encoding="utf-8") as f:
                    rec = WorkflowExecutionRecord.model_validate_json(f.read())
                    if target_model_id and rec.target_model_id != target_model_id:
                        continue
                    results.append(rec)
            except Exception:
                continue

        return results[offset : offset + limit]


# Singleton instance for Application & API Controller
agent_orchestrator = AgentWorkflowOrchestrator()
