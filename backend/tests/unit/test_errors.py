"""Unit tests for structured error handling and exception formatting."""

from unittest.mock import MagicMock

import pytest
from fastapi.exceptions import HTTPException, RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.errors import (
    create_error_response,
    db_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)


@pytest.mark.asyncio
async def test_create_error_response_format() -> None:
    response = create_error_response(
        status_code=400,
        error_code="INVALID_INPUT",
        message="The provided input is invalid",
        details={"field": "name"},
    )
    assert response.status_code == 400
    data = response.body.decode("utf-8")
    assert "INVALID_INPUT" in data
    assert "The provided input is invalid" in data


@pytest.mark.asyncio
async def test_http_exception_handler() -> None:
    mock_request = MagicMock()
    mock_request.url.path = "/test"

    exc = HTTPException(status_code=404, detail="Item not found")
    response = await http_exception_handler(mock_request, exc)

    assert response.status_code == 404
    body = response.body.decode("utf-8")
    assert "NOT_FOUND" in body
    assert "Item not found" in body


@pytest.mark.asyncio
async def test_validation_exception_handler() -> None:
    mock_request = MagicMock()
    mock_request.url.path = "/test"

    exc = RequestValidationError(
        [{"loc": ("body", "name"), "msg": "field required", "type": "value_error.missing"}]
    )
    response = await validation_exception_handler(mock_request, exc)

    assert response.status_code == 422
    body = response.body.decode("utf-8")
    assert "VALIDATION_ERROR" in body
    assert "Request validation failed" in body


@pytest.mark.asyncio
async def test_db_exception_handler() -> None:
    mock_request = MagicMock()
    mock_request.url.path = "/test"

    exc = SQLAlchemyError("Database connection lost")
    response = await db_exception_handler(mock_request, exc)

    assert response.status_code == 500
    body = response.body.decode("utf-8")
    assert "DATABASE_ERROR" in body


@pytest.mark.asyncio
async def test_generic_exception_handler() -> None:
    mock_request = MagicMock()
    mock_request.url.path = "/test"

    exc = RuntimeError("Unexpected runtime failure")
    response = await generic_exception_handler(mock_request, exc)

    assert response.status_code == 500
    body = response.body.decode("utf-8")
    assert "INTERNAL_SERVER_ERROR" in body
