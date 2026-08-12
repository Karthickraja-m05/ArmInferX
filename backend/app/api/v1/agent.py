"""ArmServe Autonomous Optimization Agent REST API Endpoints.

Provides live orchestration control over the Optimization Agent:
- POST /agent/start (Start autonomous optimization workflow)
- POST /agent/stop (Abort active agent execution)
- GET /agent/status (Current agent runtime state)
- GET /agent/history (Paginated optimization history records)
- GET /agent/recommendation (Explainable evidence-based recommendation report)
"""

import asyncio
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.app.services.agent_recommendation_engine import AGENT_RECOMMENDATIONS_DIR, AgentRecommendationEngine, AgentRecommendationReport
from backend.app.services.agent_workflow_orchestrator import (
    WorkflowExecutionRecord,
    agent_orchestrator,
)

router = APIRouter(prefix="/agent", tags=["Optimization Agent"])


class AgentStartRequest(BaseModel):
    target_model_id: str = Field(
        default="qwen2.5-0.5b-instruct",
        description="Target model identifier for optimization exploration.",
    )
    max_steps: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Maximum optimization loop iterations to execute.",
    )
    background: bool = Field(
        default=False,
        description="Whether to run the optimization workflow asynchronously in background.",
    )


class AgentStartResponse(BaseModel):
    status: str
    workflow_id: str | None = None
    target_model_id: str
    max_steps: int
    message: str
    workflow_record: WorkflowExecutionRecord | None = None


class AgentStopResponse(BaseModel):
    status: str
    workflow_id: str | None = None
    message: str


class AgentStatusResponse(BaseModel):
    status: str
    is_running: bool
    active_workflow_id: str | None = None
    active_model: str
    current_step: int
    max_steps: int
    stop_requested: bool
    latest_workflow_id: str | None = None
    latest_best_score: float | None = None


class AgentHistoryResponse(BaseModel):
    total_count: int
    limit: int
    offset: int
    workflows: list[WorkflowExecutionRecord]


@router.post(
    "/start",
    response_model=AgentStartResponse,
    status_code=status.HTTP_200_OK,
    summary="Start Autonomous Optimization Agent",
)
async def start_agent(request: AgentStartRequest) -> AgentStartResponse:
    """Start autonomous optimization agent loop."""
    current_status = agent_orchestrator.get_status()
    if current_status["is_running"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Optimization Agent is already actively running workflow '{current_status['active_workflow_id']}'.",
        )

    if request.background:
        asyncio.create_task(
            agent_orchestrator.run_autonomous_optimization_loop(
                target_model_id=request.target_model_id,
                max_steps=request.max_steps,
            )
        )
        return AgentStartResponse(
            status="STARTED_BACKGROUND",
            target_model_id=request.target_model_id,
            max_steps=request.max_steps,
            message="Autonomous optimization agent initiated in background.",
        )

    # Synchronous execution
    try:
        record = await agent_orchestrator.run_autonomous_optimization_loop(
            target_model_id=request.target_model_id,
            max_steps=request.max_steps,
        )
        return AgentStartResponse(
            status="COMPLETED",
            workflow_id=record.workflow_id,
            target_model_id=record.target_model_id,
            max_steps=request.max_steps,
            message="Autonomous optimization loop executed and converged successfully.",
            workflow_record=record,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent workflow execution failed: {str(e)}",
        )


@router.post(
    "/stop",
    response_model=AgentStopResponse,
    status_code=status.HTTP_200_OK,
    summary="Stop Autonomous Optimization Agent",
)
async def stop_agent() -> AgentStopResponse:
    """Request running autonomous optimization agent to abort execution gracefully."""
    res = agent_orchestrator.request_stop()
    return AgentStopResponse(
        status=res["status"],
        workflow_id=res.get("workflow_id"),
        message=res["message"],
    )


@router.get(
    "/status",
    response_model=AgentStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Agent Status",
)
async def get_agent_status() -> AgentStatusResponse:
    """Get current runtime status and progress of the autonomous optimization agent."""
    st = agent_orchestrator.get_status()
    return AgentStatusResponse(**st)


@router.get(
    "/history",
    response_model=AgentHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="List Agent Optimization History",
)
async def list_agent_history(
    limit: int = Query(default=10, ge=1, le=100, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    target_model_id: str | None = Query(default=None, description="Filter by model ID"),
) -> AgentHistoryResponse:
    """Retrieve paginated optimization workflows executed by the agent."""
    records = agent_orchestrator.list_workflows(limit=1000, offset=0, target_model_id=target_model_id)
    paginated = records[offset : offset + limit]
    return AgentHistoryResponse(
        total_count=len(records),
        limit=limit,
        offset=offset,
        workflows=paginated,
    )


@router.get(
    "/recommendation",
    response_model=AgentRecommendationReport,
    status_code=status.HTTP_200_OK,
    summary="Get Latest Explainable Recommendation",
)
async def get_agent_recommendation(
    workflow_id: str | None = Query(default=None, description="Optional workflow ID to retrieve specific recommendation"),
) -> AgentRecommendationReport:
    """Retrieve explainable evidence-based recommendation report generated by the agent."""
    target_file = AGENT_RECOMMENDATIONS_DIR / "latest.json"

    if workflow_id:
        # Search for recommendation with matching workflow ID
        found = False
        for f in AGENT_RECOMMENDATIONS_DIR.glob("*.json"):
            if f.name != "latest.json":
                try:
                    with open(f, "r", encoding="utf-8") as rf:
                        rep = AgentRecommendationReport.model_validate_json(rf.read())
                        if rep.workflow_id == workflow_id or rep.recommendation_id == workflow_id:
                            return rep
                except Exception:
                    continue
        if not found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No recommendation found for workflow ID '{workflow_id}'.",
            )

    if not target_file.exists():
        # If no recommendation exists yet, attempt to generate one from the latest workflow
        workflows = agent_orchestrator.list_workflows(limit=1)
        if workflows:
            engine = AgentRecommendationEngine()
            return engine.generate_recommendation(workflows[0])

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No agent recommendations available. Run an optimization loop via POST /agent/start first.",
        )

    with open(target_file, "r", encoding="utf-8") as f:
        return AgentRecommendationReport.model_validate_json(f.read())
