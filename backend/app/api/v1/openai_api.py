"""OpenAI-Compatible REST API Router for ArmServe."""

import structlog
from fastapi import APIRouter, HTTPException, status

from backend.app.services.inference_engine import (
    ChatCompletionRequest,
    CompletionRequest,
    ModelInfo,
    engine,
)

logger = structlog.get_logger("backend.app.api.v1.openai_api")

router = APIRouter(tags=["OpenAI API"])


@router.get(
    "/v1/models", response_model=dict[str, list[ModelInfo]], operation_id="list_openai_models_v1"
)
@router.get("/models", response_model=dict[str, list[ModelInfo]], operation_id="list_openai_models")
async def list_models() -> dict[str, list[ModelInfo]]:
    """List available loaded inference models."""
    return {
        "data": [
            ModelInfo(id="qwen2.5-0.5b-instruct"),
            ModelInfo(id="armserve-qwen-0.5b"),
        ]
    }


@router.post("/v1/chat/completions")
@router.post("/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest) -> dict:
    """Create an OpenAI-compatible chat completion response."""
    try:
        logger.info(
            "Handling OpenAI chat completion request",
            model=request.model,
            message_count=len(request.messages),
        )
        response = engine.generate_chat_completion(request)
        return response
    except Exception as err:
        logger.error("Chat completion error", error=str(err))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference Engine Error: {err}",
        ) from err


@router.post("/v1/completions")
@router.post("/completions")
async def create_completion(request: CompletionRequest) -> dict:
    """Create an OpenAI-compatible text completion response."""
    try:
        logger.info(
            "Handling OpenAI completion request",
            model=request.model,
            prompt_length=len(request.prompt),
        )
        response = engine.generate_completion(request)
        return response
    except Exception as err:
        logger.error("Completion error", error=str(err))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference Engine Error: {err}",
        ) from err
