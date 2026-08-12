"""Experiment management API router with real database persistence."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.core.dependencies import get_uow
from backend.app.models.experiment import ExperimentRecord
from backend.app.models.model_registry import ModelRecord, ModelVersionRecord
from backend.app.repositories.unit_of_work import UnitOfWork
from backend.app.schemas.experiment import ExperimentCreate, ExperimentResponse

router = APIRouter(prefix="/experiments", tags=["Experiments"])


@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_experiment(
    payload: ExperimentCreate,
    uow: UnitOfWork = Depends(get_uow),
) -> ExperimentResponse:
    """Create a new optimization experiment stored in the real database."""
    # Ensure target model version exists or create default model version
    model_version = await uow.model_versions.get_by_id(payload.model_id)
    if not model_version:
        model = await uow.models.get_by_id(payload.model_id)
        if not model:
            model = await uow.models.create(
                ModelRecord(id=payload.model_id, name=f"model-{payload.model_id}", framework="ONNX")
            )
        model_version = await uow.model_versions.create(
            ModelVersionRecord(model_id=model.id, version="v1.0", format="ONNX")
        )

    exp_record = ExperimentRecord(
        name=payload.name,
        model_version_id=model_version.id,
        status="CREATED",
        budget=payload.budget,
        constraints=payload.constraints.model_dump(),
        search_space=payload.search_space.model_dump(),
    )
    created_exp = await uow.experiments.create(exp_record)
    await uow.commit()

    return ExperimentResponse(
        id=created_exp.id,
        name=created_exp.name,
        status=created_exp.status,
        model_id=payload.model_id,
        constraints=payload.constraints.model_dump(),
        search_space=payload.search_space.model_dump(),
        budget=created_exp.budget,
        created_at=created_exp.created_at,
        updated_at=created_exp.updated_at,
        trials=[],
    )


@router.get("", response_model=list[ExperimentResponse])
async def list_experiments(
    uow: UnitOfWork = Depends(get_uow),
) -> list[ExperimentResponse]:
    """List all optimization experiments stored in the database."""
    experiments = await uow.experiments.list()
    result: list[ExperimentResponse] = []

    for exp in experiments:
        result.append(
            ExperimentResponse(
                id=exp.id,
                name=exp.name,
                status=exp.status,
                model_id=exp.model_version_id,
                constraints=exp.constraints,
                search_space=exp.search_space,
                budget=exp.budget,
                created_at=exp.created_at,
                updated_at=exp.updated_at,
                trials=[],
            )
        )
    return result


@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(
    experiment_id: UUID,
    uow: UnitOfWork = Depends(get_uow),
) -> ExperimentResponse:
    """Get details of a specific experiment by ID from the database."""
    exp = await uow.experiments.get_with_relations(experiment_id)
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experiment not found",
        )

    return ExperimentResponse(
        id=exp.id,
        name=exp.name,
        status=exp.status,
        model_id=exp.model_version_id,
        constraints=exp.constraints,
        search_space=exp.search_space,
        budget=exp.budget,
        created_at=exp.created_at,
        updated_at=exp.updated_at,
        trials=[],
    )
