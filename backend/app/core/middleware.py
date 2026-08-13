"""Structured HTTP request logging, security headers, and metrics collection middleware for FastAPI."""

import time
import uuid
from collections.abc import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.core.metrics import metrics_collector

logger = structlog.get_logger("backend.app.api.access")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing secure HTTP headers across all API responses."""

    async def dispatch(  # type: ignore[override]
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        response: Response = await call_next(request)  # type: ignore[misc]

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request correlation, latency measurement, and metrics collection."""

    async def dispatch(  # type: ignore[override]
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
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

        try:
            response: Response = await call_next(request)  # type: ignore[misc]
            duration_seconds = time.perf_counter() - start_time
            process_time_ms = round(duration_seconds * 1000, 2)

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time-Ms"] = str(process_time_ms)

            # Record real application metrics
            metrics_collector.record_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                duration_seconds=duration_seconds,
            )

            # Record in Observability Store
            from backend.app.core.observability import observability_store
            observability_store.record_log(
                level="INFO" if response.status_code < 400 else "ERROR",
                message=f"HTTP {request.method} {request.url.path} -> {response.status_code}",
                module="http.access",
                trace_id=request_id,
                extra={"status_code": response.status_code, "process_time_ms": process_time_ms},
            )

            logger.info(
                "HTTP Request Completed",
                status_code=response.status_code,
                process_time_ms=process_time_ms,
            )
            return response
        except Exception as exc:
            duration_seconds = time.perf_counter() - start_time
            process_time_ms = round(duration_seconds * 1000, 2)

            # Record error metrics
            err_type = type(exc).__name__
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


class MaintenanceModeMiddleware(BaseHTTPMiddleware):
    """Intercepts mutating HTTP requests when maintenance mode is toggled active."""

    async def dispatch(  # type: ignore[override]
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        from backend.app.services.health_service import health_service

        if health_service.is_maintenance_mode and request.method in ("POST", "PUT", "DELETE", "PATCH"):
            if not request.url.path.endswith("/system/maintenance"):
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": f"Service in Maintenance Mode: {health_service.maintenance_reason}",
                        "status": "MAINTENANCE",
                    },
                )

        return await call_next(request)  # type: ignore[misc]

