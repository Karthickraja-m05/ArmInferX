"""Arm Performix Benchmark, Correlation, and Evidence Generation REST API Router."""

from typing import Literal

import structlog
from fastapi import APIRouter, HTTPException, Query, Response, status

from backend.app.schemas.performix import (
    PerformixComparisonResult,
    PerformixRunRequest,
    PerformixRunResult,
)
from backend.app.services.optimization_evidence_generator import evidence_generator
from backend.app.services.performix_comparator import performix_comparator
from backend.app.services.performix_runner import performix_runner

logger = structlog.get_logger("backend.app.api.v1.performix")

router = APIRouter(prefix="/performix", tags=["Performix Integration"])


@router.post(
    "/run",
    response_model=PerformixRunResult,
    status_code=status.HTTP_201_CREATED,
    operation_id="run_performix_benchmark",
)
async def run_performix_benchmark(body: PerformixRunRequest) -> PerformixRunResult:
    """Execute real Arm Performix benchmark workload on AWS ARM64 Graviton environment."""
    try:
        result = await performix_runner.run_benchmark(body)
        return result
    except Exception as err:
        logger.error("Performix execution failed", error=str(err))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Performix benchmark error: {str(err)}",
        ) from err


@router.get("/results", response_model=dict, operation_id="get_performix_results")
async def get_performix_results(
    limit: int = Query(default=20, ge=1, le=100),
    model_id: str | None = Query(default=None),
) -> dict:
    """List historical Performix benchmark execution results with pagination and filtering."""
    all_results = performix_runner.list_results(limit=100)
    if model_id:
        all_results = [r for r in all_results if r.model_id == model_id]

    paginated = all_results[:limit]
    return {
        "total_count": len(all_results),
        "limit": limit,
        "results": [r.model_dump() for r in paginated],
    }


@router.get(
    "/comparison",
    response_model=PerformixComparisonResult,
    summary="Compare Performix vs ArmServe",
    operation_id="compare_performix_runs",
)
async def compare_performix_benchmark(
    armserve_run_id: str = Query(default="bm-run-001"),
    performix_run_id: str | None = Query(default=None),
) -> PerformixComparisonResult:
    """Correlate ArmServe internal benchmark vs official Arm Performix benchmark."""
    try:
        if not performix_run_id:
            results = performix_runner.list_results(limit=1)
            if not results:
                # Execute sample Performix run if history is empty
                req = PerformixRunRequest()
                pmx_res = await performix_runner.run_benchmark(req)
                performix_run_id = pmx_res.performix_run_id
            else:
                performix_run_id = results[0].performix_run_id

        res = performix_comparator.compare_runs(armserve_run_id, performix_run_id)
        return res
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Performix comparison failed: {str(err)}",
        ) from err


@router.get(
    "/report",
    summary="Generate Validation Evidence Report",
    operation_id="generate_performix_report",
)
async def generate_performix_report(
    format: Literal["markdown", "json", "csv"] = Query(default="markdown"),
) -> Response:
    """Generate optimization evidence report in Markdown, JSON, or CSV format for hackathon submission."""
    report = evidence_generator.generate_report(format_type=format)
    media_type = (
        "text/markdown"
        if format == "markdown"
        else "text/csv"
        if format == "csv"
        else "application/json"
    )
    return Response(content=report.content, media_type=media_type)
