"""Unit tests for Experiment Scheduler and Queue Management Engine."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.experiment_executor import ExperimentRunRecord
from backend.app.services.experiment_scheduler import ExperimentScheduler

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_scheduler_state():
    """Reset global ExperimentScheduler state between test cases."""
    scheduler = ExperimentScheduler()
    scheduler.queue.clear()
    scheduler.current_config_id = None
    scheduler.status = "IDLE"
    scheduler.completed_count = 0
    scheduler.failed_count = 0
    scheduler.scheduling_events.clear()


def test_scheduler_queue_enqueuing():
    """Test enqueuing configurations into scheduler queue."""
    scheduler = ExperimentScheduler()
    enqueued = scheduler.enqueue_configurations(["cfg-unit-1", "cfg-unit-2"])
    assert len(enqueued) == 2
    assert scheduler.get_status().pending_count == 2


@pytest.mark.asyncio
async def test_scheduler_sequential_processing():
    """Test sequential processing loop and completion tracking."""
    scheduler = ExperimentScheduler()
    scheduler.enqueue_configurations(["cfg-mock-1"])

    mock_record = ExperimentRunRecord(
        experiment_id="exp-mock-1",
        config_id="cfg-mock-1",
        status="COMPLETED",
        model_id="qwen2.5-0.5b-instruct",
        configuration={"thread_count": 4},
    )

    with patch.object(scheduler._executor, "execute_experiment", AsyncMock(return_value=mock_record)):
        records = await scheduler.process_queue()
        assert len(records) == 1
        assert records[0].status == "COMPLETED"
        assert scheduler.get_status().pending_count == 0
        assert scheduler.get_status().completed_count == 1


def test_scheduler_status_api_endpoint():
    """Test GET /api/v1/experiments/scheduler/status endpoint."""
    res = client.get("/api/v1/experiments/scheduler/status")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "queue_status" in data
    assert "pending_count" in data
    assert "completed_count" in data
