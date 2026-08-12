"""Real database integration tests exercising repository layer."""

from datetime import datetime, timezone

import pytest

from backend.app.models import (
    BenchmarkMetricRecord,
    BenchmarkRunRecord,
    DeploymentEventRecord,
    DeploymentRecord,
    ExperimentConfigurationRecord,
    ExperimentRecord,
    ModelRecord,
    ModelVersionRecord,
    OptimizationRunRecord,
    TrialRecord,
    UserRecord,
)
from backend.app.repositories.unit_of_work import UnitOfWork


@pytest.mark.asyncio
async def test_user_repository(uow: UnitOfWork) -> None:
    # Create user
    user = UserRecord(
        email="dev@armserve.io",
        hashed_password="secure_password_hash",
        full_name="ArmServe Developer",
        is_active=True,
    )
    created_user = await uow.users.create(user)
    assert created_user.id is not None

    # Fetch by ID and email
    fetched = await uow.users.get_by_id(created_user.id)
    assert fetched is not None
    assert fetched.email == "dev@armserve.io"

    fetched_by_email = await uow.users.get_by_email("dev@armserve.io")
    assert fetched_by_email is not None
    assert fetched_by_email.id == created_user.id

    # List & Count
    users_list = await uow.users.list()
    assert len(users_list) >= 1
    count = await uow.users.count()
    assert count >= 1

    # Delete
    deleted = await uow.users.delete_by_id(created_user.id)
    assert deleted is True
    assert await uow.users.get_by_id(created_user.id) is None


@pytest.mark.asyncio
async def test_model_and_version_repositories(uow: UnitOfWork) -> None:
    model = ModelRecord(
        name="llama3-8b-arm",
        description="Llama 3 8B model compiled for Arm Neoverse N2",
        framework="ONNX",
        author="Meta AI",
    )
    created_model = await uow.models.create(model)
    assert created_model.id is not None

    version1 = ModelVersionRecord(
        model_id=created_model.id,
        version="v1.0.0",
        storage_uri="s3://armserve-models/llama3/v1.0.0.onnx",
        format="ONNX",
        quantization="FP16",
        size_bytes=16000000000,
        compatible_runtimes=["onnxruntime", "executorch"],
        metadata_info={"neon_optimized": True},
    )
    created_version = await uow.model_versions.create(version1)
    assert created_version.id is not None

    # Query version by model and version name
    fetched_version = await uow.model_versions.get_by_model_and_version(created_model.id, "v1.0.0")
    assert fetched_version is not None
    assert fetched_version.quantization == "FP16"

    # List versions
    versions = await uow.model_versions.list_versions_for_model(created_model.id)
    assert len(versions) == 1
    assert versions[0].version == "v1.0.0"


@pytest.mark.asyncio
async def test_experiment_and_trial_repositories(uow: UnitOfWork) -> None:
    # Setup model and version
    model = await uow.models.create(ModelRecord(name="bert-base-uncased", framework="ONNX"))
    version = await uow.model_versions.create(
        ModelVersionRecord(model_id=model.id, version="v1.0.0", format="ONNX")
    )

    # Setup experiment
    experiment = ExperimentRecord(
        name="bert-arm64-quant-study",
        model_version_id=version.id,
        status="RUNNING",
        budget=20,
        constraints={"max_latency_ms": 15.0},
        search_space={"execution_mode": ["sequential", "parallel"]},
    )
    created_exp = await uow.experiments.create(experiment)

    # Add experiment configuration entry
    config_entry = ExperimentConfigurationRecord(
        experiment_id=created_exp.id,
        config_key="num_threads",
        config_value={"val": 8},
    )
    await uow.experiment_configurations.create(config_entry)

    # Add trials
    trial1 = TrialRecord(
        experiment_id=created_exp.id,
        trial_number=1,
        configuration={"num_threads": 8, "execution_mode": "parallel"},
        status="COMPLETED",
        benchmark_results={"latency_ms": 12.4, "throughput_qps": 85.0},
    )
    await uow.trials.create(trial1)

    # Verify eager loading & relations query
    fetched_exp = await uow.experiments.get_with_relations(created_exp.id)
    assert fetched_exp is not None
    assert len(fetched_exp.configurations) == 1
    assert fetched_exp.configurations[0].config_key == "num_threads"
    assert len(fetched_exp.trials) == 1
    assert fetched_exp.trials[0].trial_number == 1


@pytest.mark.asyncio
async def test_benchmark_run_and_metric_repositories(uow: UnitOfWork) -> None:
    model = await uow.models.create(ModelRecord(name="resnet50-v2", framework="ONNX"))
    version = await uow.model_versions.create(
        ModelVersionRecord(model_id=model.id, version="v1.0", format="ONNX")
    )

    run = BenchmarkRunRecord(
        model_version_id=version.id,
        hardware_target="aws-graviton3",
        runtime_name="onnxruntime",
        status="COMPLETED",
        configuration={"batch_size": 32, "thread_count": 16},
    )
    created_run = await uow.benchmark_runs.create(run)

    now = datetime.now(timezone.utc)
    metrics = [
        BenchmarkMetricRecord(
            benchmark_run_id=created_run.id,
            timestamp=now,
            metric_name="latency_p99",
            metric_value=4.25,
            unit="ms",
        ),
        BenchmarkMetricRecord(
            benchmark_run_id=created_run.id,
            timestamp=now,
            metric_name="cpu_utilization",
            metric_value=78.5,
            unit="percent",
        ),
    ]

    await uow.benchmark_metrics.add_metrics_batch(metrics)

    fetched_metrics = await uow.benchmark_metrics.list_for_run(created_run.id)
    assert len(fetched_metrics) == 2
    metric_names = [m.metric_name for m in fetched_metrics]
    assert "latency_p99" in metric_names
    assert "cpu_utilization" in metric_names


@pytest.mark.asyncio
async def test_optimization_run_repository(uow: UnitOfWork) -> None:
    model = await uow.models.create(ModelRecord(name="opt-model-1", framework="ONNX"))
    version = await uow.model_versions.create(
        ModelVersionRecord(model_id=model.id, version="v1.0", format="ONNX")
    )
    experiment = await uow.experiments.create(
        ExperimentRecord(name="opt-exp-1", model_version_id=version.id)
    )

    opt_run = OptimizationRunRecord(
        experiment_id=experiment.id,
        strategy="TPE",
        status="IN_PROGRESS",
        max_trials=50,
        trials_completed=5,
    )
    created_opt = await uow.optimization_runs.create(opt_run)
    assert created_opt.id is not None

    opt_runs = await uow.optimization_runs.list_for_experiment(experiment.id)
    assert len(opt_runs) == 1
    assert opt_runs[0].strategy == "TPE"


@pytest.mark.asyncio
async def test_deployment_and_event_repositories(uow: UnitOfWork) -> None:
    model = await uow.models.create(ModelRecord(name="deploy-model", framework="ONNX"))
    version = await uow.model_versions.create(
        ModelVersionRecord(model_id=model.id, version="v1.0", format="ONNX")
    )

    deployment = DeploymentRecord(
        name="prod-arm-endpoint-1",
        model_version_id=version.id,
        environment="production",
        status="ACTIVE",
        replicas=4,
        endpoint_url="http://inference.armserve.internal/v1/predict",
    )
    created_deploy = await uow.deployments.create(deployment)

    event = DeploymentEventRecord(
        deployment_id=created_deploy.id,
        event_type="SCALE",
        message="Scaled out replicas from 2 to 4",
        details={"previous_replicas": 2, "new_replicas": 4},
    )
    await uow.deployment_events.create(event)

    deployments = await uow.deployments.list_by_environment("production")
    assert len(deployments) == 1
    assert deployments[0].name == "prod-arm-endpoint-1"

    events = await uow.deployment_events.list_events_for_deployment(created_deploy.id)
    assert len(events) == 1
    assert events[0].event_type == "SCALE"
