"""Benchmark Execution REST API Router."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
import structlog

from backend.app.services.benchmark_runner import (
    BenchmarkConfig,
    BenchmarkRunResult,
    BenchmarkRunner,
    BENCHMARKS_DIR,
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
async def list_benchmarks() -> list[dict]:
    """List historical benchmark run manifests."""
    BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)
    manifests = []
    for manifest_path in BENCHMARKS_DIR.glob("*.json"):
        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifests.append(json.load(f))
        except Exception as err:
            logger.warning("Failed to read benchmark manifest", path=str(manifest_path), error=str(err))
    return manifests
