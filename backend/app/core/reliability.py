"""ArmServe Platform Reliability Engineering Module.

Provides circuit breaker strategy, exponential backoff retries with jitter,
timeout handling, workflow state persistence & resumption, and idempotent operation management.
"""

import asyncio
import functools
import json
import random
import time
from collections.abc import Callable
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar

import structlog

from backend.app.core.metrics import metrics_collector

logger = structlog.get_logger("backend.app.core.reliability")

T = TypeVar("T")
WORKFLOW_STORAGE_DIR = Path("storage/workflows")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"  # Normal operation: traffic flows freely
    OPEN = "OPEN"  # Tripped state: calls fail immediately
    HALF_OPEN = "HALF_OPEN"  # Trial state: testing upstream recovery


class CircuitBreakerOpenException(Exception):
    """Raised when an operation is attempted on an OPEN circuit breaker."""

    def __init__(self, breaker_name: str, recovery_seconds_remaining: float):
        self.breaker_name = breaker_name
        self.recovery_seconds_remaining = recovery_seconds_remaining
        super().__init__(
            f"Circuit breaker '{breaker_name}' is OPEN. "
            f"Retry allowed in {recovery_seconds_remaining:.1f}s."
        )


class CircuitBreaker:
    """Thread-safe and async-compatible Circuit Breaker implementation."""

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_success_threshold: int = 2,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_success_threshold = half_open_success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_state_change = time.time()
        self._last_failure_time = 0.0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        # Check for automatic transition from OPEN to HALF_OPEN after recovery_timeout
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                logger.info(
                    "Circuit breaker transitioned to HALF_OPEN",
                    breaker=self.name,
                )
        return self._state

    def _record_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.half_open_success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                self._last_state_change = time.time()
                logger.info("Circuit breaker reset to CLOSED", breaker=self.name)
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0

    def _record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._state in (CircuitState.CLOSED, CircuitState.HALF_OPEN):
            if self._failure_count >= self.failure_threshold or self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._last_state_change = time.time()
                metrics_collector.record_error(
                    error_type="CircuitBreakerTripped",
                    status_code=503,
                    endpoint=f"circuit:{self.name}",
                )
                logger.error(
                    "Circuit breaker TRIPPED to OPEN",
                    breaker=self.name,
                    failures=self._failure_count,
                    recovery_timeout=self.recovery_timeout,
                )

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute callable protected by the circuit breaker."""
        async with self._lock:
            current_state = self.state
            if current_state == CircuitState.OPEN:
                remaining = max(0.0, self.recovery_timeout - (time.time() - self._last_failure_time))
                raise CircuitBreakerOpenException(self.name, remaining)

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            async with self._lock:
                self._record_success()
            return result
        except Exception as exc:
            async with self._lock:
                self._record_failure()
            raise exc

    def get_status(self) -> dict[str, Any]:
        """Return diagnostic metrics snapshot for the circuit breaker."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_seconds": self.recovery_timeout,
            "last_failure_timestamp": self._last_failure_time,
            "uptime_seconds": round(time.time() - self._last_state_change, 2),
        }


# Global registry of circuit breakers for agent, deployment, optimization APIs
circuit_breakers: dict[str, CircuitBreaker] = {
    "agent_engine": CircuitBreaker(name="agent_engine", failure_threshold=3, recovery_timeout=15.0),
    "deployment_api": CircuitBreaker(name="deployment_api", failure_threshold=4, recovery_timeout=20.0),
    "optimization_engine": CircuitBreaker(name="optimization_engine", failure_threshold=3, recovery_timeout=15.0),
    "external_storage": CircuitBreaker(name="external_storage", failure_threshold=5, recovery_timeout=30.0),
}


def get_circuit_breaker(name: str) -> CircuitBreaker:
    """Retrieve or dynamically create named CircuitBreaker instance."""
    if name not in circuit_breakers:
        circuit_breakers[name] = CircuitBreaker(name=name)
    return circuit_breakers[name]


async def retry_with_backoff(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int = 3,
    initial_delay: float = 0.1,
    backoff_factor: float = 2.0,
    max_delay: float = 10.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    **kwargs: Any,
) -> Any:
    """Execute function with exponential backoff and randomized jitter retries."""
    delay = initial_delay
    last_exception: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)
        except retryable_exceptions as exc:
            last_exception = exc
            if attempt == max_retries:
                logger.error(
                    "Max retries exhausted for operation",
                    attempt=attempt,
                    max_retries=max_retries,
                    error=str(exc),
                )
                raise exc

            current_delay = delay
            if jitter:
                current_delay *= random.uniform(0.8, 1.2)  # nosec B311

            logger.warning(
                "Operation failed; scheduling retry with backoff",
                attempt=attempt,
                max_retries=max_retries,
                delay_seconds=round(current_delay, 3),
                error=str(exc),
            )
            await asyncio.sleep(current_delay)
            delay = min(delay * backoff_factor, max_delay)

    if last_exception:
        raise last_exception


async def with_timeout(
    coro_or_func: Callable[..., Any] | Any,
    timeout_seconds: float = 30.0,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Execute asynchronous task with strict timeout threshold."""
    try:
        if callable(coro_or_func):
            coro = coro_or_func(*args, **kwargs) if asyncio.iscoroutinefunction(coro_or_func) else coro_or_func(*args, **kwargs)
        else:
            coro = coro_or_func
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.error("Operation timed out", timeout_seconds=timeout_seconds)
        raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds")


class IdempotentOperationManager:
    """Manages idempotency keys to prevent duplicate execution of mutating API workflows."""

    def __init__(self, cache_file: Path = WORKFLOW_STORAGE_DIR / "idempotency.json"):
        self.cache_file = cache_file
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, dict[str, Any]] = self._load_cache()

    def _load_cache(self) -> dict[str, dict[str, Any]]:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self) -> None:
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
        except Exception as err:
            logger.warning("Failed to persist idempotency cache", error=str(err))

    def get_cached_result(self, idempotency_key: str) -> dict[str, Any] | None:
        """Return cached result if idempotency key exists and is valid."""
        return self._cache.get(idempotency_key)

    def record_result(self, idempotency_key: str, result_data: dict[str, Any]) -> None:
        """Record completed execution output under idempotency key."""
        self._cache[idempotency_key] = {
            "result": result_data,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        self._save_cache()


class WorkflowRecoveryManager:
    """Workflow state persistence engine enabling safe recovery after service restart."""

    def __init__(self, storage_dir: Path = WORKFLOW_STORAGE_DIR):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.storage_dir / "workflow_states.json"
        self._workflows: dict[str, dict[str, Any]] = self._load_states()

    def _load_states(self) -> dict[str, dict[str, Any]]:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_states(self) -> None:
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self._workflows, f, indent=2)
        except Exception as err:
            logger.warning("Failed to persist workflow recovery state", error=str(err))

    def save_checkpoint(
        self,
        workflow_id: str,
        workflow_type: str,
        current_step: str,
        status: str,
        context_data: dict[str, Any],
    ) -> None:
        """Save workflow checkpoint state."""
        self._workflows[workflow_id] = {
            "workflow_id": workflow_id,
            "workflow_type": workflow_type,
            "current_step": current_step,
            "status": status,  # "PENDING", "RUNNING", "FAILED", "COMPLETED"
            "context_data": context_data,
            "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        self._save_states()
        logger.info(
            "Saved workflow checkpoint",
            workflow_id=workflow_id,
            step=current_step,
            status=status,
        )

    def get_pending_workflows(self) -> list[dict[str, Any]]:
        """Retrieve all workflows that were in RUNNING or PENDING state before service restart."""
        return [
            wf for wf in self._workflows.values()
            if wf.get("status") in ("PENDING", "RUNNING")
        ]

    def recover_and_resume_workflows(self) -> int:
        """Scan state manifest and reset interrupted RUNNING workflows to PENDING for recovery."""
        interrupted = self.get_pending_workflows()
        count = 0
        for wf in interrupted:
            wf["status"] = "PENDING"
            wf["recovered_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            count += 1
        if count > 0:
            self._save_states()
            logger.info("Recovered interrupted background workflows on service restart", count=count)
        return count


# Singletons
idempotency_manager = IdempotentOperationManager()
workflow_recovery_manager = WorkflowRecoveryManager()
