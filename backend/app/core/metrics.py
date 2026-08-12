"""ArmServe Metrics and Observability Abstraction Layer.

Provides thread-safe application metrics collection (request latency, request counts,
error counts, and database operation metrics) and standard Prometheus text format export.
"""

import re
import threading
import time
from collections import defaultdict
from typing import Any


class MetricsCollector:
    """Thread-safe application metrics collector for ArmServe."""

    # Standard Prometheus histogram buckets for HTTP latency (in seconds)
    LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._start_time = time.time()

        # Counter: (method, endpoint, status_code) -> count
        self._request_counts: dict[tuple[str, str, str], int] = defaultdict(int)

        # Histogram: (method, endpoint) -> bucket_counts, total_sum, total_count
        self._request_latencies: dict[tuple[str, str], dict[str, Any]] = defaultdict(
            lambda: {
                "buckets": defaultdict(int),
                "sum": 0.0,
                "count": 0,
            }
        )

        # Error Counter: (error_type, status_code, endpoint) -> count
        self._error_counts: dict[tuple[str, str, str], int] = defaultdict(int)

        # DB Operation Counter: (operation, status) -> count
        self._db_op_counts: dict[tuple[str, str], int] = defaultdict(int)

        # DB Latency: operation -> sum, count
        self._db_op_latencies: dict[str, dict[str, float]] = defaultdict(
            lambda: {"sum": 0.0, "count": 0.0}
        )

    def normalize_endpoint(self, path: str) -> str:
        """Normalize URL path parameters to prevent high metric cardinality.

        Example: /api/v1/experiments/f8397530-6e08-4b08-aba5 -> /api/v1/experiments/{id}
        """
        # Replace UUIDs
        path = re.sub(
            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
            "{id}",
            path,
        )
        # Replace integer IDs
        path = re.sub(r"/\d+(?=/|$)", "/{id}", path)
        return path

    def record_request(
        self, method: str, endpoint: str, status_code: int, duration_seconds: float
    ) -> None:
        """Record an incoming HTTP request execution."""
        clean_endpoint = self.normalize_endpoint(endpoint)
        status_str = str(status_code)
        method_upper = method.upper()

        with self._lock:
            # 1. Request Counter
            self._request_counts[(method_upper, clean_endpoint, status_str)] += 1

            # 2. Latency Histogram
            latency_entry = self._request_latencies[(method_upper, clean_endpoint)]
            latency_entry["count"] += 1
            latency_entry["sum"] += duration_seconds

            for bucket in self.LATENCY_BUCKETS:
                if duration_seconds <= bucket:
                    latency_entry["buckets"][bucket] += 1

            # 3. Automatic Error Counter for 4xx/5xx
            if status_code >= 400:
                err_type = "HTTPClientError" if status_code < 500 else "HTTPServerError"
                self._error_counts[(err_type, status_str, clean_endpoint)] += 1

    def record_error(self, error_type: str, status_code: int, endpoint: str) -> None:
        """Record an application or system error event."""
        clean_endpoint = self.normalize_endpoint(endpoint)
        status_str = str(status_code)
        with self._lock:
            self._error_counts[(error_type, status_str, clean_endpoint)] += 1

    def record_db_operation(self, operation: str, status: str, duration_seconds: float) -> None:
        """Record a database query or connection check operation."""
        op_lower = operation.lower()
        status_lower = status.lower()
        with self._lock:
            self._db_op_counts[(op_lower, status_lower)] += 1
            entry = self._db_op_latencies[op_lower]
            entry["sum"] += duration_seconds
            entry["count"] += 1.0

    def get_summary(self) -> dict[str, Any]:
        """Return a structured dictionary snapshot of recorded metrics."""
        with self._lock:
            total_requests = sum(self._request_counts.values())
            total_errors = sum(self._error_counts.values())
            total_db_ops = sum(self._db_op_counts.values())

            return {
                "uptime_seconds": round(time.time() - self._start_time, 2),
                "total_requests": total_requests,
                "total_errors": total_errors,
                "total_db_operations": total_db_ops,
                "requests_by_status": {
                    f"{m} {ep} {st}": cnt for (m, ep, st), cnt in self._request_counts.items()
                },
                "errors_by_type": {
                    f"{t} ({st}) {ep}": cnt for (t, st, ep), cnt in self._error_counts.items()
                },
                "db_operations": {
                    f"{op} ({st})": cnt for (op, st), cnt in self._db_op_counts.items()
                },
            }

    def generate_prometheus_text(self) -> str:
        """Generate Prometheus exposition text format (version=0.0.4)."""
        lines: list[str] = []

        with self._lock:
            # 1. System Info Gauge
            lines.append("# HELP armserve_app_info ArmServe application metadata")
            lines.append("# TYPE armserve_app_info gauge")
            lines.append('armserve_app_info{app="armserve",version="0.1.0",arch="arm64"} 1')
            lines.append("")

            # 2. HTTP Requests Total Counter
            lines.append("# HELP http_requests_total Total number of HTTP requests processed")
            lines.append("# TYPE http_requests_total counter")
            for (method, endpoint, status_code), count in sorted(self._request_counts.items()):
                lines.append(
                    f'http_requests_total{{method="{method}",endpoint="{endpoint}",status="{status_code}"}} {count}'
                )
            lines.append("")

            # 3. HTTP Request Duration Histogram
            lines.append("# HELP http_request_duration_seconds HTTP request latency histogram")
            lines.append("# TYPE http_request_duration_seconds histogram")
            for (method, endpoint), data in sorted(self._request_latencies.items()):
                cumulative_count = 0
                for bucket in self.LATENCY_BUCKETS:
                    cumulative_count += data["buckets"][bucket]
                    lines.append(
                        f'http_request_duration_seconds_bucket{{method="{method}",endpoint="{endpoint}",le="{bucket}"}} {cumulative_count}'
                    )
                lines.append(
                    f'http_request_duration_seconds_bucket{{method="{method}",endpoint="{endpoint}",le="+Inf"}} {data["count"]}'
                )
                lines.append(
                    f'http_request_duration_seconds_sum{{method="{method}",endpoint="{endpoint}"}} {data["sum"]:.6f}'
                )
                lines.append(
                    f'http_request_duration_seconds_count{{method="{method}",endpoint="{endpoint}"}} {data["count"]}'
                )
            lines.append("")

            # 4. HTTP Errors Total Counter
            lines.append("# HELP http_errors_total Total number of HTTP/application errors")
            lines.append("# TYPE http_errors_total counter")
            for (error_type, status_code, endpoint), count in sorted(self._error_counts.items()):
                lines.append(
                    f'http_errors_total{{error_type="{error_type}",status="{status_code}",endpoint="{endpoint}"}} {count}'
                )
            lines.append("")

            # 5. DB Operations Counter & Latencies
            lines.append("# HELP db_operations_total Total database operations performed")
            lines.append("# TYPE db_operations_total counter")
            for (op, status), count in sorted(self._db_op_counts.items()):
                lines.append(f'db_operations_total{{operation="{op}",status="{status}"}} {count}')
            lines.append("")

            lines.append(
                "# HELP db_operation_duration_seconds_sum Total database operation duration"
            )
            lines.append("# TYPE db_operation_duration_seconds_sum counter")
            for op, data in sorted(self._db_op_latencies.items()):
                lines.append(
                    f'db_operation_duration_seconds_sum{{operation="{op}"}} {data["sum"]:.6f}'
                )
                lines.append(
                    f'db_operation_duration_seconds_count{{operation="{op}"}} {int(data["count"])}'
                )
            lines.append("")

        return "\n".join(lines) + "\n"


# Global singleton instance for application metrics
metrics_collector = MetricsCollector()
