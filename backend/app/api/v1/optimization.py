"""ArmServe Optimization REST API Router.

Exposes endpoints for running full optimization pipelines, setting SLA constraints,
fetching normalized results, retrieving configuration rankings, and obtaining evidence-based recommendations.
"""

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
import structlog

from backend.app.services.configuration_ranker import ConfigurationRanker, RankingReport
from backend.app.services.constraint_engine import ConstraintEngine, ConstraintSpec
from backend.app.services.experiment_executor import ExperimentExecutor
from backend.app.services.metrics_normalizer import MetricsNormalizer
from backend.app.services.recommendation_engine import RECOMMENDATIONS_DIR, OptimizationRecommendation, RecommendationEngine
from backend.app.services.scoring_engine import ObjectiveWeights

logger = structlog.get_logger("backend.app.api.v1.optimization")

router = APIRouter(prefix="/optimization", tags=["Optimization"])

# Global active SLA constraint spec
_active_constraint_spec: ConstraintSpec = ConstraintSpec()


@router.post("/constraints", response_model=ConstraintSpec)
async def update_optimization_constraints(spec: ConstraintSpec) -> ConstraintSpec:
    """Update global active SLA constraint specification."""
    global _active_constraint_spec
    _active_constraint_spec = spec
    logger.info("Updated optimization SLA constraints", spec=spec.model_dump())
    return _active_constraint_spec


@router.post("/run", response_model=OptimizationRecommendation)
async def run_optimization_pipeline(
    weights: Optional[ObjectiveWeights] = None,
    constraints: Optional[ConstraintSpec] = None,
) -> OptimizationRecommendation:
    """Execute end-to-end optimization pipeline: normalization, scoring, SLA checking, ranking, & recommendation."""
    runs = ExperimentExecutor.list_experiments()
    if not runs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No historical experiment runs available. Execute experiments first.",
        )

    spec = constraints or _active_constraint_spec
    ranker = ConfigurationRanker()
    ranking_report = ranker.rank_experiment_runs(runs, constraint_spec=spec, weights=weights)

    # Use first run as baseline if multiple runs exist
    baseline = runs[-1] if len(runs) > 1 else None

    rec_engine = RecommendationEngine()
    recommendation = rec_engine.generate_recommendation(ranking_report, baseline_run=baseline)
    return recommendation


@router.get("/results", response_model=dict)
async def get_optimization_results(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    model_id: Optional[str] = Query(None),
) -> dict:
    """Retrieve raw and normalized experiment metrics datasets with pagination."""
    runs = ExperimentExecutor.list_experiments(model_id_filter=model_id)

    # Normalize
    snapshots = MetricsNormalizer.normalize_benchmark_runs(runs)
    snap_map = {s.run_id: s for s in snapshots}

    combined = []
    for r in runs:
        exp_id = r.get("experiment_id") or r.get("run_id")
        snap = snap_map.get(exp_id)
        combined.append(
            {
                "experiment_id": exp_id,
                "config_id": r.get("config_id"),
                "status": r.get("status"),
                "raw_metrics": r.get("metrics_summary"),
                "normalized_metrics": snap.model_dump() if snap else None,
            }
        )

    start = (page - 1) * size
    end = start + size
    paginated = combined[start:end]

    return {
        "page": page,
        "size": size,
        "total": len(combined),
        "results": paginated,
    }


@router.get("/rankings", response_model=RankingReport)
async def get_optimization_rankings(
    constraints: Optional[ConstraintSpec] = None,
    weights: Optional[ObjectiveWeights] = None,
    top_n: int = Query(10, ge=1, le=100),
) -> RankingReport:
    """Retrieve current ranked configuration report based on active SLA constraints."""
    runs = ExperimentExecutor.list_experiments()
    spec = constraints or _active_constraint_spec
    ranker = ConfigurationRanker()
    return ranker.rank_experiment_runs(runs, constraint_spec=spec, weights=weights, top_n=top_n)


@router.get("/recommendation", response_model=OptimizationRecommendation)
async def get_latest_recommendation() -> OptimizationRecommendation:
    """Retrieve latest generated optimization recommendation manifest."""
    RECOMMENDATIONS_DIR.mkdir(parents=True, exist_ok=True)
    recs = list(RECOMMENDATIONS_DIR.glob("*.json"))
    if not recs:
        # Run default recommendation pipeline
        return await run_optimization_pipeline()

    # Pick newest
    recs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    with open(recs[0], encoding="utf-8") as f:
        data = json.load(f)
        return OptimizationRecommendation(**data)
