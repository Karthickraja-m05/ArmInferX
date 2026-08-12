"""Model management API router with real database persistence."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.core.dependencies import get_uow
from backend.app.models.model_registry import ModelRecord
from backend.app.repositories.unit_of_work import UnitOfWork
from backend.app.schemas.model import ModelRegister, ModelResponse

router = APIRouter(prefix="/models", tags=["Models"])


@router.post("", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def register_model(
    payload: ModelRegister,
    uow: UnitOfWork = Depends(get_uow),
) -> ModelResponse:
    """Register a new AI model in the real database registry."""
    existing = await uow.models.get_by_name(payload.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Model with name '{payload.name}' already exists.",
        )

    model_record = ModelRecord(
        name=payload.name,
        framework=payload.format,
        author=payload.source,
    )
    created_model = await uow.models.create(model_record)
    await uow.commit()

    return ModelResponse(
        id=created_model.id,
        name=created_model.name,
        source=payload.source,
        format=created_model.framework,
        quantization=payload.quantization,
        size_bytes=0,
        storage_uri=f"s3://armserve-models/{created_model.name}",
        compatible_runtimes=["onnxruntime"],
        metadata_info={"status": "registered"},
        created_at=created_model.created_at,
        updated_at=created_model.updated_at,
    )


@router.get("", response_model=list[ModelResponse])
async def list_models(
    uow: UnitOfWork = Depends(get_uow),
) -> list[ModelResponse]:
    """List all registered models stored in the database."""
    models = await uow.models.list()
    result: list[ModelResponse] = []

    for m in models:
        result.append(
            ModelResponse(
                id=m.id,
                name=m.name,
                source=m.author or "unknown",
                format=m.framework,
                quantization="NONE",
                size_bytes=0,
                storage_uri=f"s3://armserve-models/{m.name}",
                compatible_runtimes=["onnxruntime"],
                metadata_info={"status": "registered"},
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
        )
    return result


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: UUID,
    uow: UnitOfWork = Depends(get_uow),
) -> ModelResponse:
    """Get details of a specific model by ID from database."""
    model = await uow.models.get_by_id(model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    return ModelResponse(
        id=model.id,
        name=model.name,
        source=model.author or "unknown",
        format=model.framework,
        quantization="NONE",
        size_bytes=0,
        storage_uri=f"s3://armserve-models/{model.name}",
        compatible_runtimes=["onnxruntime"],
        metadata_info={"status": "registered"},
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
