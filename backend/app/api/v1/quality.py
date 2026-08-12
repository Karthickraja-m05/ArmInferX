"""ArmServe Quality Evaluation REST API Endpoints.

Provides REST endpoints for executing quality evaluation runs, querying evaluation results,
retrieving evaluation reports, and performing baseline quality comparison.
"""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.app.services.quality_comparator import QualityComparator, QualityComparisonReport
from backend.app.services.quality_reporter import QualityReporter
from backend.app.services.quality_response_collector import QualityResponseCollector
from backend.app.services.quality_scoring_engine import QualityEvaluationReport, QualityScoringEngine

router = APIRouter(prefix="/quality", tags=["quality"])

response_collector = QualityResponseCollector()
scoring_engine = QualityScoringEngine()
comparator = QualityComparator()
reporter = QualityReporter()


class QualityRunRequest(BaseModel):
    config_id: str = Field(default="cfg-002d5491f3", description="Target inference runtime config ID")
    experiment_id: str = Field(default="exp-1786554838", description="Target experiment ID")
    dataset_id: str = Field(default="eval-core-v1", description="Evaluation dataset ID")
    baseline_eval_id: str | None = Field(default=None, description="Optional baseline evaluation ID for automated comparison")
    allowed_degradation_pct: float = Field(default=2.0, ge=0.0, le=50.0, description="Max allowed percentage degradation threshold")


class QualityRunResponse(BaseModel):
    evaluation: QualityEvaluationReport
    comparison: QualityComparisonReport | None = None
    markdown_report: str


@router.post("/run", response_model=QualityRunResponse, status_code=status.HTTP_200_OK)
async def run_quality_evaluation(payload: QualityRunRequest) -> QualityRunResponse:
    """Execute live response collection, score quality, and optionally compare against baseline."""
    try:
        # 1. Collect responses
        collection = await response_collector.collect_dataset_responses(
            config_id=payload.config_id,
            experiment_id=payload.experiment_id,
            dataset_id=payload.dataset_id,
        )

        # 2. Score evaluation
        eval_report = scoring_engine.evaluate_collection_record(collection)

        # 3. Optional comparison with baseline
        comp_report: QualityComparisonReport | None = None
        if payload.baseline_eval_id:
            baseline_file = Path("storage/quality/evaluations") / f"{payload.baseline_eval_id}.json"
            if baseline_file.exists():
                import json
                with open(baseline_file, encoding="utf-8") as f:
                    b_data = json.load(f)
                    b_report = QualityEvaluationReport(**b_data)
                    comp_report = comparator.compare_evaluations(
                        baseline_report=b_report,
                        target_report=eval_report,
                        allowed_degradation_pct=payload.allowed_degradation_pct,
                    )

        # 4. Generate Markdown report
        md_report = reporter.generate_markdown_report(eval_report, comp_report)
        reporter.generate_json_report(eval_report, comp_report)
        reporter.generate_csv_report(eval_report)

        return QualityRunResponse(
            evaluation=eval_report,
            comparison=comp_report,
            markdown_report=md_report,
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute quality evaluation: {err}",
        ) from err


@router.get("/results", status_code=status.HTTP_200_OK)
def list_quality_results(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    config_id: str | None = Query(default=None),
) -> dict[str, Any]:
    """Retrieve paginated list of quality evaluation reports."""
    import json
    eval_files = list(Path("storage/quality/evaluations").glob("*.json"))
    eval_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    items: list[dict[str, Any]] = []
    for f in eval_files:
        try:
            with open(f, encoding="utf-8") as f_in:
                data = json.load(f_in)
                if config_id and data.get("config_id") != config_id:
                    continue
                items.append(data)
        except Exception:
            pass

    total = len(items)
    start_idx = (page - 1) * size
    paginated_items = items[start_idx : start_idx + size]

    return {
        "total": total,
        "page": page,
        "size": size,
        "items": paginated_items,
    }


@router.get("/comparison", response_model=QualityComparisonReport, status_code=status.HTTP_200_OK)
def get_quality_comparison(
    baseline_id: str = Query(..., description="Baseline Evaluation ID"),
    target_id: str = Query(..., description="Target Evaluation ID"),
    allowed_degradation_pct: float = Query(default=2.0, ge=0.0, le=50.0),
) -> QualityComparisonReport:
    """Compare baseline quality evaluation against target quality evaluation."""
    import json
    b_file = Path("storage/quality/evaluations") / f"{baseline_id}.json"
    t_file = Path("storage/quality/evaluations") / f"{target_id}.json"

    if not b_file.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Baseline evaluation '{baseline_id}' not found.")
    if not t_file.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Target evaluation '{target_id}' not found.")

    with open(b_file, encoding="utf-8") as f:
        b_report = QualityEvaluationReport(**json.load(f))
    with open(t_file, encoding="utf-8") as f:
        t_report = QualityEvaluationReport(**json.load(f))

    return comparator.compare_evaluations(
        baseline_report=b_report,
        target_report=t_report,
        allowed_degradation_pct=allowed_degradation_pct,
    )


@router.get("/{id}", status_code=status.HTTP_200_OK)
def get_quality_evaluation_by_id(id: str) -> dict[str, Any]:
    """Retrieve specific quality evaluation report by ID."""
    import json
    target_file = Path("storage/quality/evaluations") / f"{id}.json"
    if not target_file.exists():
        # Try matching substring
        matches = list(Path("storage/quality/evaluations").glob(f"*{id}*.json"))
        if not matches:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Quality evaluation report '{id}' not found.")
        target_file = matches[0]

    with open(target_file, encoding="utf-8") as f:
        return json.load(f)
