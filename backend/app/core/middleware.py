"""Structured HTTP request logging, security headers, and metrics collection middleware for FastAPI.

All middleware is implemented as pure ASGI middleware (not BaseHTTPMiddleware) to avoid
ClientDisconnected crashes from anyio TaskGroups when Render's proxy disconnects mid-response.
"""

import time
import uuid

import structlog
from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.app.core.metrics import metrics_collector

logger = structlog.get_logger("backend.app.api.access")

try:
    _BaseExceptionGroup: type[BaseException] = BaseExceptionGroup  # type: ignore[name-defined]
except NameError:
    try:
        from exceptiongroup import (
            BaseExceptionGroup as _BaseExceptionGroup,  # type: ignore[no-redef]
        )
    except ImportError:
        _BaseExceptionGroup = ()  # type: ignore[assignment,misc]


def _is_client_disconnect(exc: BaseException) -> bool:
    """Check if an exception (possibly wrapped in ExceptionGroup) is a client disconnect."""
    name = type(exc).__name__
    if name in ("ClientDisconnect", "ClientDisconnected"):
        return True
    # Python 3.11+ / exceptiongroup ExceptionGroups from anyio TaskGroups
    if isinstance(exc, _BaseExceptionGroup) or hasattr(exc, "exceptions"):
        exceptions = getattr(exc, "exceptions", ())
        return all(_is_client_disconnect(e) for e in exceptions)
    return False


class ClientDisconnectMiddleware:
    """Pure ASGI middleware that absorbs client-disconnect errors.

    Wraps the entire ASGI chain and silently absorbs ClientDisconnected exceptions
    that occur when the Render proxy (TTL=4s) or the browser disconnects before
    the response body is fully delivered.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            try:
                await send(message)
            except Exception as exc:
                if _is_client_disconnect(exc):
                    logger.debug(
                        "Client disconnected during response",
                        path=scope.get("path", "unknown"),
                    )
                    return
                raise

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            if _is_client_disconnect(exc):
                logger.debug(
                    "Client disconnected during request",
                    path=scope.get("path", "unknown"),
                )
                return
            raise


class SecurityHeadersMiddleware:
    """Pure ASGI middleware enforcing secure HTTP headers across all API responses."""

    SECURITY_HEADERS: dict[str, str] = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    }

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for key, value in self.SECURITY_HEADERS.items():
                    headers.append(key, value)
            await send(message)

        await self.app(scope, receive, send_with_headers)


class RequestLoggingMiddleware:
    """Pure ASGI middleware for request correlation, latency measurement, and metrics collection."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        start_time = time.perf_counter()
        client_ip = request.client.host if request.client else "unknown"

        # Contextualize structlog for thread/task scope
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
            client_ip=client_ip,
        )

        status_code = 500  # Default if we never see a response.start

        async def send_with_logging(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = MutableHeaders(scope=message)
                duration_seconds = time.perf_counter() - start_time
                process_time_ms = round(duration_seconds * 1000, 2)
                headers.append("X-Request-ID", request_id)
                headers.append("X-Process-Time-Ms", str(process_time_ms))
            await send(message)

        try:
            await self.app(scope, receive, send_with_logging)

            duration_seconds = time.perf_counter() - start_time
            process_time_ms = round(duration_seconds * 1000, 2)

            # Record real application metrics
            metrics_collector.record_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=status_code,
                duration_seconds=duration_seconds,
            )

            # Record in Observability Store
            from backend.app.core.observability import observability_store

            observability_store.record_log(
                level="INFO" if status_code < 400 else "ERROR",
                message=f"HTTP {request.method} {request.url.path} -> {status_code}",
                module="http.access",
                trace_id=request_id,
                extra={"status_code": status_code, "process_time_ms": process_time_ms},
            )

            logger.info(
                "HTTP Request Completed",
                status_code=status_code,
                process_time_ms=process_time_ms,
            )
        except Exception as exc:
            duration_seconds = time.perf_counter() - start_time
            process_time_ms = round(duration_seconds * 1000, 2)

            err_type = type(exc).__name__

            # Don't record client disconnects as server errors
            if not _is_client_disconnect(exc):
                metrics_collector.record_error(
                    error_type=err_type,
                    status_code=500,
                    endpoint=request.url.path,
                )
                metrics_collector.record_request(
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=500,
                    duration_seconds=duration_seconds,
                )
                logger.error(
                    "HTTP Request Failed",
                    error=str(exc),
                    error_type=err_type,
                    process_time_ms=process_time_ms,
                    exc_info=True,
                )

            raise


class MaintenanceModeMiddleware:
    """Pure ASGI middleware that intercepts mutating HTTP requests during maintenance mode."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from backend.app.services.health_service import health_service

        request = Request(scope)

        if health_service.is_maintenance_mode and request.method in (
            "POST",
            "PUT",
            "DELETE",
            "PATCH",
        ):
            if not request.url.path.endswith("/system/maintenance"):
                response = JSONResponse(
                    status_code=503,
                    content={
                        "detail": f"Service in Maintenance Mode: {health_service.maintenance_reason}",
                        "status": "MAINTENANCE",
                    },
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)
