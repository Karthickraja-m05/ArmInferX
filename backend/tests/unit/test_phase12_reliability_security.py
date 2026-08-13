"""Comprehensive Phase 12 Reliability, Security, Observability, Scalability, Backup, and Operational API Test Suite."""

import asyncio
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.app.core.observability import TraceContext, observability_store
from backend.app.core.reliability import (
    CircuitBreaker,
    CircuitBreakerOpenException,
    CircuitState,
    IdempotentOperationManager,
    WorkflowRecoveryManager,
    retry_with_backoff,
    with_timeout,
)
from backend.app.core.scalability import ConcurrencyLimiter, WorkloadType, scalability_manager
from backend.app.core.security import AuthContext, Role, Scope, hash_api_key, verify_api_key
from backend.app.main import app
from backend.app.services.alert_service import alert_service
from backend.app.services.backup_service import backup_service
from backend.app.services.health_service import health_service

client = TestClient(app)


# 1. Reliability & Circuit Breaker Tests
@pytest.mark.asyncio
async def test_circuit_breaker_state_transitions():
    cb = CircuitBreaker(name="test_cb", failure_threshold=2, recovery_timeout=0.2)
    assert cb.state == CircuitState.CLOSED

    # Failure 1
    with pytest.raises(ValueError):
        await cb.call(lambda: (_ for _ in ()).throw(ValueError("Fail 1")))
    assert cb.state == CircuitState.CLOSED

    # Failure 2 -> Tripped to OPEN
    with pytest.raises(ValueError):
        await cb.call(lambda: (_ for _ in ()).throw(ValueError("Fail 2")))
    assert cb.state == CircuitState.OPEN

    # Next call fails with CircuitBreakerOpenException immediately
    with pytest.raises(CircuitBreakerOpenException) as exc_info:
        await cb.call(lambda: "should not run")
    assert "OPEN" in str(exc_info.value)

    # Wait for recovery timeout -> transitions to HALF_OPEN
    await asyncio.sleep(0.25)
    assert cb.state == CircuitState.HALF_OPEN

    # Successful calls reset state to CLOSED
    res1 = await cb.call(lambda: "ok1")
    res2 = await cb.call(lambda: "ok2")
    assert res1 == "ok1" and res2 == "ok2"
    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_retry_with_exponential_backoff():
    attempts = 0

    async def flaky_func():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError(f"Transient error {attempts}")
        return "success"

    result = await retry_with_backoff(
        flaky_func,
        max_retries=3,
        initial_delay=0.01,
        backoff_factor=2.0,
    )
    assert result == "success"
    assert attempts == 3


@pytest.mark.asyncio
async def test_timeout_handling():
    async def slow_func():
        await asyncio.sleep(0.2)
        return "done"

    with pytest.raises(TimeoutError):
        await with_timeout(slow_func, timeout_seconds=0.05)


def test_idempotency_and_workflow_recovery(tmp_path: Path):
    idempotency_file = tmp_path / "idempotency.json"
    mgr = IdempotentOperationManager(cache_file=idempotency_file)

    key = "idem-key-12345"
    assert mgr.get_cached_result(key) is None

    mgr.record_result(key, {"job_status": "COMPLETED", "output": "ok"})
    cached = mgr.get_cached_result(key)
    assert cached is not None
    assert cached["result"]["job_status"] == "COMPLETED"

    # Workflow recovery testing
    wf_mgr = WorkflowRecoveryManager(storage_dir=tmp_path / "workflows")
    wf_mgr.save_checkpoint("wf-001", "optimization", "step_2", "RUNNING", {"trial": 5})

    pending = wf_mgr.get_pending_workflows()
    assert len(pending) == 1
    assert pending[0]["workflow_id"] == "wf-001"

    recovered_count = wf_mgr.recover_and_resume_workflows()
    assert recovered_count == 1


# 2. Security & Verification Tests
def test_api_key_hashing_and_verification():
    raw_key = "arm_live_secret_key_9999"
    hashed = hash_api_key(raw_key)
    assert len(hashed) == 64
    assert verify_api_key(raw_key, raw_key) is True
    assert verify_api_key("wrong_key", raw_key) is False


def test_auth_context_scope_permissions():
    context = AuthContext(
        subject_id="test-operator",
        role=Role.OPERATOR,
        scopes={Scope.READ, Scope.WRITE, Scope.MODELS_READ},
    )
    assert context.has_scope(Scope.READ) is True
    assert context.has_scope(Scope.MODELS_READ) is True
    assert context.has_scope(Scope.SYSTEM_CONFIG) is False


# 3. Observability & Tracing Tests
def test_observability_store_and_trace_context(tmp_path: Path):
    ctx = TraceContext()
    assert ctx.trace_id is not None
    child = ctx.create_child_span()
    assert child.trace_id == ctx.trace_id
    assert child.parent_span_id == ctx.span_id

    entry = observability_store.record_log(
        level="ERROR",
        message="Test observable event",
        module="test_module",
        trace_id=ctx.trace_id,
        extra={"error_code": 500},
    )
    assert entry["level"] == "ERROR"

    logs, total = observability_store.query_logs(
        level="ERROR",
        trace_id=ctx.trace_id,
    )
    assert total >= 1
    assert logs[0]["message"] == "Test observable event"


# 4. Backup & Disaster Recovery Tests
def test_backup_create_verify_and_restore(tmp_path: Path):
    bm_svc = backup_service
    test_backup_id = f"test-bk-{int(time.time())}"

    manifest = bm_svc.create_backup(backup_id=test_backup_id)
    assert manifest.backup_id == test_backup_id
    assert manifest.sha256_checksum is not None

    verified = bm_svc.verify_backup(test_backup_id)
    assert verified is True

    restore_target = tmp_path / "restore_dest"
    restore_res = bm_svc.restore_backup(test_backup_id, target_dir=restore_target)
    assert restore_res["status"] == "SUCCESS"
    assert restore_res["files_restored"] > 0

    dr_result = bm_svc.run_recovery_test()
    assert dr_result["overall_result"] == "PASS"


# 5. Alerting & Resource Monitoring Tests
def test_alert_service_evaluations():
    alert = alert_service.trigger_alert(
        rule_name="TestHighLatency",
        severity="HIGH",
        message="Latency exceeded 500ms threshold",
        component="api.latency",
        metric_value=550.0,
        threshold_value=500.0,
    )
    assert alert.alert_id.startswith("alert-")
    assert alert.status == "ACTIVE"

    resolved = alert_service.resolve_alert(alert.alert_id)
    assert resolved is not None
    assert resolved.status == "RESOLVED"

    alerts, total = alert_service.get_alerts(severity="HIGH")
    assert total >= 1


# 6. Concurrency & Scalability Tests
@pytest.mark.asyncio
async def test_concurrency_limiter_workload_isolation():
    limiter = ConcurrencyLimiter(max_concurrent_jobs=2, max_queue_depth=2)

    assert await limiter.acquire() is True
    assert await limiter.acquire() is True

    stats = limiter.get_stats()
    assert stats.active_jobs == 2

    limiter.release()
    stats = limiter.get_stats()
    assert stats.active_jobs == 1
    limiter.release()

    res = await scalability_manager.schedule_job(
        WorkloadType.EXPERIMENT,
        lambda: "scaled_result",
    )
    assert res == "scaled_result"


# 7. Operational REST APIs Tests
def test_operational_apis():
    # 1. GET /system/status
    res = client.get("/system/status")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "status" in data
    assert "subsystems" in data

    # 2. GET /system/metrics
    res = client.get("/system/metrics")
    assert res.status_code == status.HTTP_200_OK
    assert "total_requests" in res.json()

    res_prom = client.get("/system/metrics?format=prometheus")
    assert res_prom.status_code == status.HTTP_200_OK
    assert "http_requests_total" in res_prom.text

    # 3. GET /system/logs
    res = client.get("/system/logs?limit=10")
    assert res.status_code == status.HTTP_200_OK
    assert "logs" in res.json()

    # 4. GET /system/alerts
    res = client.get("/system/alerts")
    assert res.status_code == status.HTTP_200_OK
    assert "alerts" in res.json()

    # 5. GET /system/diagnostics
    res = client.get("/system/diagnostics")
    assert res.status_code == status.HTTP_200_OK
    assert "system_resources" in res.json()
    assert "circuit_breakers" in res.json()


def test_maintenance_mode_interceptor():
    # Enable Maintenance Mode
    res = client.post("/system/maintenance?enabled=true&reason=Unit+Testing+Maintenance")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["maintenance_mode"] is True

    # Mutating request should be blocked with 503
    blocked_res = client.post("/api/v1/benchmarks/run", json={"model_id": "test"})
    assert blocked_res.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "Maintenance Mode" in blocked_res.json()["detail"]

    # Disable Maintenance Mode
    disable_res = client.post("/system/maintenance?enabled=false")
    assert disable_res.status_code == status.HTTP_200_OK
    assert disable_res.json()["maintenance_mode"] is False
