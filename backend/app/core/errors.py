"""Global structured error handling and exception handlers for FastAPI."""

from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import Request, status
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.schemas.error import ErrorResponse

logger = structlog.get_logger(__name__)


def create_error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: list[dict[str, Any]] | dict[str, Any] | None = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error_code=error_code,
        message=message,
        timestamp=datetime.now(timezone.utc),
        details=details,
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle explicit FastAPI/Starlette HTTPExceptions with structured payload."""
    status_code = getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
    detail = getattr(exc, "detail", "An HTTP error occurred")

    error_code = "NOT_FOUND" if status_code == 404 else f"HTTP_{status_code}"
    message = detail if isinstance(detail, str) else str(detail)

    logger.warning(
        "HTTP exception occurred",
        path=request.url.path,
        status_code=status_code,
        detail=message,
    )
    return create_error_response(
        status_code=status_code,
        error_code=error_code,
        message=message,
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle Pydantic / FastAPI request validation failures."""
    raw_errors: list[Any] = getattr(exc, "errors", lambda: [])()
    logger.warning(
        "Request validation error",
        path=request.url.path,
        errors_count=len(raw_errors),
    )

    formatted_errors = [
        {
            "loc": [str(item) for item in err.get("loc", [])],
            "msg": str(err.get("msg", "")),
            "type": str(err.get("type", "")),
        }
        for err in raw_errors
    ]

    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        details=formatted_errors,
    )


async def db_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle database layer errors safely without exposing internal details."""
    logger.error(
        "Database exception caught in API layer",
        path=request.url.path,
        error=str(exc),
        exc_info=True,
    )
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="DATABASE_ERROR",
        message="A database processing error occurred",
        details={"path": request.url.path} if settings.app.debug else None,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled server exceptions."""
    logger.error(
        "Unhandled exception in API request",
        path=request.url.path,
        error=str(exc),
        exc_info=True,
    )
    details = {"type": exc.__class__.__name__, "error": str(exc)} if settings.app.debug else None

    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred",
        details=details,
    )
