# ADR 0001: FastAPI for Backend API Framework

## Status
Accepted

## Context
ArmServe requires an asynchronous, high-performance API framework capable of handling concurrent client requests, WebSocket streaming for real-time benchmark event monitoring, and automatic OpenAPI schema generation for CLI and SDK clients.

## Decision
We choose **FastAPI** (Python 3.11+) as the core framework for the Backend API.

## Rationale
1. **Native Async Support**: Built on Starlette and asyncio, allowing non-blocking database queries and event dispatching.
2. **Type Safety & Data Validation**: Uses Pydantic v2 for high-speed serialization/deserialization and rigorous request payload validation.
3. **OpenAPI & JSON Schema**: Generates interactive API documentation automatically, speeding up CLI development.
4. **Ecosystem Alignment**: Integrates seamlessly with Python's AI/ML ecosystem (ONNX Runtime, Optuna, PyTorch).

## Consequences
- Requires async-compatible libraries across the stack (e.g., `asyncpg`, `SQLAlchemy 2.0 async`).
- Developers must strictly adhere to async/await patterns to prevent blocking the event loop.
