"""ArmServe Observability, Structured Log Store, and Distributed Tracing Module.

Provides distributed tracing context propagation (Trace ID, Span ID), log correlation across
request lifecycles, structured log buffer & persistent log querying, and operational diagnostics.
"""

import asyncio
import json
from pathlib import Path
import time
import uuid
from typing import Any

import structlog

logger = structlog.get_logger("backend.app.core.observability")

OBSERVABILITY_DIR = Path("storage/observability")


class TraceContext:
    """Distributed tracing context container."""

    def __init__(self, trace_id: str | None = None, span_id: str | None = None, parent_span_id: str | None = None):
        self.trace_id = trace_id or str(uuid.uuid4())
        self.span_id = span_id or str(uuid.uuid4())[:16]
        self.parent_span_id = parent_span_id
        self.start_time = time.time()

    def create_child_span(self) -> "TraceContext":
        """Create child trace context for downstream component execution."""
        return TraceContext(
            trace_id=self.trace_id,
            span_id=str(uuid.uuid4())[:16],
            parent_span_id=self.span_id,
        )

    def to_headers(self) -> dict[str, str]:
        """Format trace context into standard HTTP headers."""
        headers = {
            "X-Trace-ID": self.trace_id,
            "X-Span-ID": self.span_id,
        }
        if self.parent_span_id:
            headers["X-Parent-Span-ID"] = self.parent_span_id
        return headers


class ObservabilityStore:
    """Thread-safe persistent log store and ring buffer for correlated application diagnostics."""

    def __init__(self, storage_dir: Path = OBSERVABILITY_DIR, max_ring_buffer_size: int = 2000):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.storage_dir / "application_logs.jsonl"
        self.max_ring_buffer_size = max_ring_buffer_size
        self._ring_buffer: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()

    def record_log(
        self,
        level: str,
        message: str,
        module: str = "app",
        trace_id: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record structured log event into ring buffer and log file."""
        log_entry = {
            "log_id": str(uuid.uuid4()),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level": level.upper(),
            "message": message,
            "module": module,
            "trace_id": trace_id or str(uuid.uuid4()),
            "details": extra or {},
        }

        # Maintain ring buffer size
        self._ring_buffer.append(log_entry)
        if len(self._ring_buffer) > self.max_ring_buffer_size:
            self._ring_buffer.pop(0)

        # Append to persistent JSONL log file
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as err:
            logger.warning("Failed to persist structured log event", error=str(err))

        return log_entry

    def query_logs(
        self,
        level: str | None = None,
        module: str | None = None,
        trace_id: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Query correlated logs with filtering and pagination."""
        logs_to_search = list(self._ring_buffer)

        # Fallback to reading file if ring buffer is smaller than requested limit/offset
        if self.log_file.exists() and len(logs_to_search) < (offset + limit):
            try:
                file_logs = []
                with open(self.log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            file_logs.append(json.loads(line.strip()))
                logs_to_search = file_logs
            except Exception:
                pass

        # Apply Filters
        filtered = logs_to_search
        if level:
            filtered = [l for l in filtered if l.get("level") == level.upper()]
        if module:
            filtered = [l for l in filtered if l.get("module") == module]
        if trace_id:
            filtered = [l for l in filtered if l.get("trace_id") == trace_id]
        if search:
            search_lower = search.lower()
            filtered = [
                l for l in filtered
                if search_lower in l.get("message", "").lower()
                or search_lower in str(l.get("details", "")).lower()
            ]

        # Reverse chronological ordering (newest first)
        filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        total = len(filtered)
        paginated = filtered[offset : offset + limit]

        return paginated, total


observability_store = ObservabilityStore()
