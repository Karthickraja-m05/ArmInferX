"""Structured HTTP request logging middleware for FastAPI."""

import time
import uuid
from collections.abc import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger("backend.app.api.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for measuring request duration and outputting structured JSON logs."""

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
            process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time-Ms"] = str(process_time_ms)

            logger.info(
                "HTTP Request Completed",
                status_code=response.status_code,
                process_time_ms=process_time_ms,
            )
            return response
        except Exception as exc:
            process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                "HTTP Request Failed",
                error=str(exc),
                process_time_ms=process_time_ms,
                exc_info=True,
            )
            raise
