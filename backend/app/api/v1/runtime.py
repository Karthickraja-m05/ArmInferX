"""Backend Runtime Integration & Model Lifecycle API Router."""

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.services.inference_engine import (
    ChatCompletionRequest,
    engine,
)
from backend.app.services.runtime_manager import runtime_manager

logger = structlog.get_logger("backend.app.api.v1.runtime")

router = APIRouter(tags=["Runtime & Model Lifecycle"])


class InferenceRequestPayload(BaseModel):
    prompt: str
    model: str = Field(default="qwen2.5-0.5b-instruct")
    max_tokens: int = Field(default=256, ge=1, le=4096)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)


@router.get("/runtime/status", operation_id="get_runtime_status")
@router.get("/api/v1/runtime/status", operation_id="get_api_v1_runtime_status")
async def get_runtime_status() -> dict:
    """Check inference runtime status, active model, and engine telemetry."""
    return runtime_manager.get_runtime_status()


@router.get("/models", operation_id="discover_models_list")
@router.get("/api/v1/models/discover", operation_id="discover_api_v1_models_list")
async def discover_models() -> dict[str, list[dict]]:
    """Discover available models and their metadata."""
    return {"data": runtime_manager.discover_models()}


@router.post("/inference", operation_id="post_inference_direct")
@router.post("/api/v1/inference", operation_id="post_api_v1_inference_direct")
async def execute_inference(payload: InferenceRequestPayload) -> dict:
    """Send inference request to the real inference runtime."""
    try:
        logger.info(
            "Handling direct inference request", prompt_len=len(payload.prompt), model=payload.model
        )
        from backend.app.services.inference_engine import ChatMessage

        chat_req = ChatCompletionRequest(
            model=payload.model,
            messages=[ChatMessage(role="user", content=payload.prompt)],
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            top_p=payload.top_p,
        )
        response = engine.generate_chat_completion(chat_req)
        return response
    except Exception as err:
        logger.error("Inference execution failed", error=str(err))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference execution failed: {err}",
        ) from err


@router.post("/api/v1/models/{model_id}/load", operation_id="load_model_by_id")
async def load_model(model_id: str) -> dict:
    """Load model into runtime memory."""
    try:
        return runtime_manager.load_model(model_id)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load model {model_id}: {err}",
        ) from err


@router.post("/api/v1/models/{model_id}/unload", operation_id="unload_model_by_id")
async def unload_model(model_id: str) -> dict:
    """Unload model from runtime memory."""
    try:
        return runtime_manager.unload_model(model_id)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unload model {model_id}: {err}",
        ) from err


@router.post("/api/v1/models/{model_id}/reload", operation_id="reload_model_by_id")
async def reload_model(model_id: str) -> dict:
    """Reload model into runtime memory."""
    try:
        return runtime_manager.reload_model(model_id)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload model {model_id}: {err}",
        ) from err


@router.get("/api/v1/models/{model_id}/status", operation_id="get_model_status_by_id")
async def get_model_status(model_id: str) -> dict:
    """Query model lifecycle status."""
    return runtime_manager.get_model_status(model_id)
