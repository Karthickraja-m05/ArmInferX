# ArmServe Observability & Metrics Guide

This document describes the observability architecture, structured JSON logging, credential masking, metrics collection, and local inspection workflows for ArmServe.

---

## 1. Observability Architecture Overview

The observability layer is built on a clean abstraction layer ([`backend/app/core/metrics.py`](file:///c:/Users/mm989/Downloads/Study/ArmInferX/backend/app/core/metrics.py)) that records **real application performance metrics** during actual request handling and database operations without using mock or synthetic data.

```
Incoming Request
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  RequestLoggingMiddleware                                   │
│  - Generates/extracts X-Request-ID (correlation ID)         │
│  - Measures exact request latency                           │
│  - Contextualizes structlog task scope                      │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────┴─────────────────────┐
        │                                           │
        ▼                                           ▼
┌────────────────────────────────┐    ┌───────────────────────────────┐
│  Structlog Logging Pipeline    │    │  MetricsCollector Abstraction │
│  - Log Levels (INFO, WARN, ERR)│    │  - Request Counters           │
│  - JSON Renderer               │    │  - Latency Histograms         │
│  - Automatic Credential Masking│    │  - Error Counters             │
└────────────────────────────────┘    │  - DB Operation Counters      │
                                      └──────────────┬────────────────┘
                                                     │
                                                     ▼
                                      ┌───────────────────────────────┐
                                      │  Prometheus Text Exporter     │
                                      │  GET /metrics                 │
                                      │  GET /api/v1/system/metrics   │
                                      └───────────────────────────────┘
```

---

## 2. Structured JSON Logging & Correlation IDs

ArmServe uses `structlog` to emit structured JSON logs. Every request is automatically tagged with:
- `request_id`: Correlation UUID (`X-Request-ID` header) propagated across async handlers.
- `method`: HTTP method (`GET`, `POST`, etc.).
- `path`: Request URL path.
- `client_ip`: Origin IP address.
- `process_time_ms`: Server-side processing latency.
- `status_code`: Response HTTP status.

### Automatic Credential & Secret Masking
To protect user privacy and comply with security rules, the structlog processor [`mask_sensitive_data`](file:///c:/Users/mm989/Downloads/Study/ArmInferX/backend/app/core/logging.py) automatically redacts any event fields containing sensitive keywords (e.g. `password`, `api_key`, `token`, `secret`, `authorization`, `credentials`):

```json
{
  "event": "User login attempt",
  "username": "alice",
  "password": "********",
  "api_key": "********",
  "request_id": "f38173cf-cc4b-42c0-b875-004aa458703d",
  "timestamp": "2026-08-12T21:25:00.123456Z",
  "level": "info"
}
```

---

## 3. Real Application Metrics

All metrics collected originate directly from application execution:

| Metric Name | Type | Description | Labels |
|---|---|---|---|
| `armserve_app_info` | Gauge | Application version and platform metadata | `app`, `version`, `arch` |
| `http_requests_total` | Counter | Total HTTP requests processed | `method`, `endpoint`, `status` |
| `http_request_duration_seconds` | Histogram | Request latency distribution in seconds | `method`, `endpoint`, `le` |
| `http_errors_total` | Counter | Application and HTTP error count | `error_type`, `status`, `endpoint` |
| `db_operations_total` | Counter | Real database queries and health checks | `operation`, `status` |
| `db_operation_duration_seconds_sum` | Counter | Accumulated database operation latency | `operation` |

---

## 4. Local Inspection Workflows

### Inspecting Logs Locally
To view structured JSON logs locally during backend execution:

```bash
# Run backend locally
uvicorn backend.app.main:app --port 8000 --reload
```

Logs will be printed to standard output (`sys.stdout`) formatted as JSON objects.

### Inspecting Metrics via HTTP Endpoints
You can view Prometheus-formatted metrics directly using `curl` or a web browser:

```bash
# Root metrics endpoint (scraped by Prometheus container)
curl http://localhost:8000/metrics

# System API metrics endpoint
curl http://localhost:8000/api/v1/system/metrics
```

Example Prometheus exposition output:
```text
# HELP armserve_app_info ArmServe application metadata
# TYPE armserve_app_info gauge
armserve_app_info{app="armserve",arch="arm64",version="0.1.0"} 1

# HELP http_requests_total Total number of HTTP requests processed
# TYPE http_requests_total counter
http_requests_total{endpoint="/api/v1/system/health",method="GET",status="200"} 12

# HELP http_request_duration_seconds HTTP request latency histogram
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{endpoint="/api/v1/system/health",le="0.05",method="GET"} 12
http_request_duration_seconds_sum{endpoint="/api/v1/system/health",method="GET"} 0.048123
http_request_duration_seconds_count{endpoint="/api/v1/system/health",method="GET"} 12
```

### Inspecting Health & Readiness Probes
```bash
# Application Liveness Probe
curl http://localhost:8000/health

# Infrastructure & Database Readiness Probe
curl http://localhost:8000/ready
```

### Running Prometheus & Grafana Locally (Docker Compose)
To run Prometheus and Grafana locally:

```bash
# Start Prometheus and Grafana services
docker compose up -d prometheus grafana

# Access Prometheus UI
http://localhost:9090

# Access Grafana UI
http://localhost:3000 (login: admin / admin)
```
