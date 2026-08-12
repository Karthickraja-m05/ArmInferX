"""Benchmark Execution & Telemetry Comparison REST API Router."""

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
import structlog

from backend.app.services.benchmark_comparator import BenchmarkComparator, BenchmarkComparisonReport
from backend.app.services.benchmark_runner import (
    BENCHMARKS_DIR,
    BenchmarkConfig,
    BenchmarkRunResult,
    BenchmarkRunner,
)

logger = structlog.get_logger("backend.app.api.v1.benchmarks")

router = APIRouter(tags=["Benchmarks"])


@router.post("/benchmarks/run", response_model=BenchmarkRunResult, operation_id="run_benchmark_direct")
@router.post("/api/v1/benchmarks/run", response_model=BenchmarkRunResult, operation_id="run_benchmark_api_v1")
async def run_benchmark(config: BenchmarkConfig) -> BenchmarkRunResult:
    """Execute a real benchmark workload against the inference engine."""
    try:
        logger.info("Handling benchmark run request", iterations=config.iterations, concurrency=config.concurrency)
        runner = BenchmarkRunner(config)
        result = await runner.run_benchmark()
        return result
    except Exception as err:
        logger.error("Benchmark run failed", error=str(err))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Benchmark execution error: {err}",
        ) from err


@router.get("/benchmarks", response_model=list[dict], operation_id="list_benchmarks_direct")
@router.get("/api/v1/benchmarks", response_model=list[dict], operation_id="list_benchmarks_api_v1")
async def list_benchmarks(
    model_id: Optional[str] = Query(None, description="Filter by model ID"),
    search: Optional[str] = Query(None, description="Search run_id or environment"),
) -> list[dict]:
    """List historical benchmark run manifests with optional filtering and search."""
    BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)
    manifests = []
    for manifest_path in sorted(BENCHMARKS_DIR.glob("*.json"), reverse=True):
        try:
            with open(manifest_path, encoding="utf-8") as f:
                data = json.load(f)

            # Filtering logic
            if model_id and data.get("config", {}).get("model_id") != model_id:
                continue
            if search:
                s_lower = search.lower()
                run_id = str(data.get("run_id", "")).lower()
                env_str = str(data.get("environment", {})).lower()
                if s_lower not in run_id and s_lower not in env_str:
                    continue

            manifests.append(data)
        except Exception as err:
            logger.warning("Failed to read benchmark manifest", path=str(manifest_path), error=str(err))
    return manifests


@router.post("/benchmarks/compare", response_model=BenchmarkComparisonReport, operation_id="compare_benchmarks_direct")
@router.post("/api/v1/benchmarks/compare", response_model=BenchmarkComparisonReport, operation_id="compare_benchmarks_api_v1")
async def compare_benchmarks(run_a_id: str, run_b_id: str) -> BenchmarkComparisonReport:
    """Compare two benchmark runs and compute absolute/percentage performance variations."""
    try:
        return BenchmarkComparator.compare_runs(run_a_id, run_b_id)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except Exception as err:
        logger.error("Benchmark comparison error", error=str(err))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Comparison failed: {err}",
        ) from err
