"""Optimization Experiment Execution & Configuration REST API Router."""

import json
from pathlib import Path
import time
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status
import structlog

from backend.app.services.experiment_executor import EXPERIMENT_RUNS_DIR, ExperimentExecutor, ExperimentRunRecord
from backend.app.services.experiment_generator import (
    CONFIGS_DIR,
    ConfigurationGenerator,
    ExperimentConfigRecord,
    ParameterRangeSpec,
)

logger = structlog.get_logger("backend.app.api.v1.experiments")

router = APIRouter(tags=["Experiments"])


@router.post("/experiments", status_code=status.HTTP_201_CREATED, response_model=dict, operation_id="create_experiment_direct")
@router.post("/api/v1/experiments", status_code=status.HTTP_201_CREATED, response_model=dict, operation_id="create_experiment_api_v1")
async def create_experiment(payload: dict) -> dict:
    """Create a new experiment record."""
    exp_id = str(uuid4())
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    record = {
        "id": exp_id,
        "experiment_id": exp_id,
        "name": payload.get("name", "optimization-exp"),
        "status": "CREATED",
        "model_id": payload.get("model_id", "qwen2.5-0.5b-instruct"),
        "constraints": payload.get("constraints", {}),
        "search_space": payload.get("search_space", {}),
        "budget": payload.get("budget", 10),
        "started_at": now_str,
        "configuration": payload,
    }
    out_file = EXPERIMENT_RUNS_DIR / f"{exp_id}.json"
    EXPERIMENT_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(record, indent=2))
    return record


@router.post("/experiments/generate", response_model=list[ExperimentConfigRecord], operation_id="generate_experiment_configs_direct")
@router.post("/api/v1/experiments/generate", response_model=list[ExperimentConfigRecord], operation_id="generate_experiment_configs_api_v1")
async def generate_experiment_configs(spec: ParameterRangeSpec) -> list[ExperimentConfigRecord]:
    """Generate valid, deduplicated experiment configuration manifests."""
    try:
        generator = ConfigurationGenerator()
        configs = generator.generate_configurations(spec)
        return configs
    except Exception as err:
        logger.error("Configuration generation error", error=str(err))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate configurations: {err}",
        ) from err


@router.post("/experiments/execute", response_model=ExperimentRunRecord, operation_id="execute_experiment_direct")
@router.post("/api/v1/experiments/execute", response_model=ExperimentRunRecord, operation_id="execute_experiment_api_v1")
async def execute_experiment(config_id: str) -> ExperimentRunRecord:
    """Execute a real parameter optimization experiment against the inference runtime."""
    try:
        executor = ExperimentExecutor()
        record = await executor.execute_experiment(config_id)
        return record
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except Exception as err:
        logger.error("Experiment execution error", error=str(err))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Experiment execution failed: {err}",
        ) from err


@router.get("/experiments", response_model=list[dict], operation_id="list_experiments_direct")
@router.get("/api/v1/experiments", response_model=list[dict], operation_id="list_experiments_api_v1")
async def list_experiments(
    status_filter: Optional[str] = Query(None, description="Filter by status (COMPLETED, FAILED, RUNNING)"),
    model_id: Optional[str] = Query(None, description="Filter by model ID"),
) -> list[dict]:
    """List historical experiment run manifests with filtering."""
    return ExperimentExecutor.list_experiments(status_filter=status_filter, model_id_filter=model_id)


@router.get("/experiments/{exp_id}", response_model=dict, operation_id="get_experiment_by_id_direct")
@router.get("/api/v1/experiments/{exp_id}", response_model=dict, operation_id="get_experiment_by_id_api_v1")
async def get_experiment_by_id(exp_id: str) -> dict:
    """Retrieve single experiment run manifest by ID."""
    file_path = EXPERIMENT_RUNS_DIR / f"{exp_id}.json"
    if not file_path.exists():
        matches = list(EXPERIMENT_RUNS_DIR.glob(f"*{exp_id}*.json"))
        if not matches:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Experiment '{exp_id}' not found.",
            )
        file_path = matches[0]

    with open(file_path, encoding="utf-8") as f:
        return json.load(f)
