# ArmServe — Architecture Overview

> Autonomous AI Inference Optimization and Deployment Platform for Arm64 Cloud Infrastructure

## 1. Mission

ArmServe automates the full lifecycle of AI model deployment on Arm64 cloud infrastructure:

1. Accept a model and performance requirements.
2. Explore the configuration space (runtime, quantization, instance type, CPU tuning).
3. Execute real benchmarks on real Arm64 hardware.
4. Evaluate inference quality against ground truth.
5. Select the configuration that best satisfies latency, throughput, cost, and quality constraints.
6. Deploy the selected configuration to production infrastructure.
7. Monitor deployed services continuously.
8. Re-optimize when constraints are violated.

**No simulation. No fake data. No placeholder integrations.**

---

## 2. System Boundary

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ArmServe Platform                          │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  ┌───────────┐  │
│  │ Frontend │  │   CLI    │  │   Backend API    │  │ Scheduler │  │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  └─────┬─────┘  │
│       │              │                 │                   │        │
│       └──────────────┴────────┬────────┘                   │        │
│                               │                            │        │
│                     ┌─────────▼──────────┐                 │        │
│                     │  Optimization      │◄────────────────┘        │
│                     │  Controller        │                          │
│                     └─────────┬──────────┘                          │
│                               │                                     │
│              ┌────────────────┼────────────────┐                    │
│              ▼                ▼                ▼                     │
│  ┌───────────────┐ ┌──────────────┐ ┌──────────────────┐           │
│  │ Optimization  │ │  Experiment  │ │  Model           │           │
│  │ Agent         │ │  Manager     │ │  Management      │           │
│  └───────┬───────┘ └──────┬───────┘ └────────┬─────────┘           │
│          │                │                   │                     │
│          ▼                ▼                   ▼                     │
│  ┌───────────────┐ ┌──────────────┐ ┌──────────────────┐           │
│  │ Benchmark     │ │  Quality     │ │  Cost            │           │
│  │ Engine        │ │  Evaluation  │ │  Analysis        │           │
│  └───────┬───────┘ └──────────────┘ └──────────────────┘           │
│          │                                                          │
│          ▼                                                          │
│  ┌───────────────┐ ┌──────────────┐ ┌──────────────────┐           │
│  │ Inference     │ │  Cloud Infra │ │  Deployment      │           │
│  │ Service       │ │  Manager     │ │  Manager         │           │
│  └───────────────┘ └──────────────┘ └──────────────────┘           │
│                                                                     │
│  ┌───────────────┐ ┌──────────────┐ ┌──────────────────┐           │
│  │ Metrics       │ │ Observability│ │  Database        │           │
│  │ Collection    │ │              │ │  (PG + TS + Redis│           │
│  └───────────────┘ └──────────────┘ └──────────────────┘           │
│                                                                     │
│  Infrastructure: Terraform │ CI/CD: GitHub Actions                  │
└─────────────────────────────────────────────────────────────────────┘

External Dependencies:
  - AWS (Graviton instances: c7g, m7g, r7g)
  - Azure (Cobalt 100 instances)
  - GCP (Axion instances)
  - HuggingFace Hub (model downloads)
  - S3-compatible storage (model artifacts)
  - Container registry (inference images)
```

---

## 3. Design Principles

| Principle | Rationale |
|-----------|-----------|
| **Real execution only** | Every benchmark, inference, and deployment must run on real hardware. No simulation. |
| **Incremental implementation** | Architecture supports building one component at a time. Phase 1 can run without Phase 3 components. |
| **Explicit boundaries** | Every component has a defined interface. No implicit coupling. |
| **Async by default for long operations** | Benchmarks, optimizations, and deployments are asynchronous tasks. Status is queryable. |
| **Sync for queries and CRUD** | API reads, metadata queries, and configuration updates are synchronous request-response. |
| **Fail loud** | Errors surface immediately. No silent fallbacks to mocks or defaults. |
| **Configuration over code** | Runtime behavior is driven by configuration, not hardcoded values. |
| **Observable** | Every operation emits structured logs, metrics, and traces. |
| **Idempotent operations** | Long-running operations can be safely retried after failure. |
| **Cloud-agnostic core** | Core logic does not depend on a specific cloud provider. Provider adapters implement a common interface. |

---

## 4. Component Summary

| # | Component | Primary Technology | Communication |
|---|-----------|-------------------|---------------|
| 1 | Frontend | React 18 + Vite + TypeScript | REST API, WebSocket |
| 2 | Backend API | FastAPI (Python 3.11+) | REST (external), Celery (internal) |
| 3 | Optimization Controller | Python module | Celery tasks, database |
| 4 | Optimization Agent | Python + Optuna | Called by Controller via Celery |
| 5 | Experiment Manager | Python module | Database, called by API/Controller |
| 6 | Benchmark Engine | Python, runs on Arm64 targets | gRPC to/from Controller, SSH to targets |
| 7 | Inference Service | ONNX Runtime, llama.cpp, vLLM | HTTP/gRPC inference endpoints |
| 8 | Model Management | Python + S3 SDK | REST API, S3 storage |
| 9 | Quality Evaluation | Python + evaluation libraries | Called by Controller, reads inference outputs |
| 10 | Cost Analysis | Python + cloud pricing APIs | Called by Controller, cloud billing APIs |
| 11 | Cloud Infrastructure Manager | Python + Terraform + cloud SDKs | Cloud provider APIs |
| 12 | Deployment Manager | Python + Kubernetes client | Kubernetes API |
| 13 | Metrics Collection | Prometheus + custom collectors | Prometheus scrape, push gateway |
| 14 | Observability | structlog + OpenTelemetry + Grafana | Log aggregation, OTLP |
| 15 | Database | PostgreSQL 16 + TimescaleDB + Redis 7 | SQL (asyncpg), Redis protocol |
| 16 | CLI | Python (Typer) | REST API calls to Backend |
| 17 | Infrastructure-as-Code | Terraform | Terraform Cloud/CLI |
| 18 | CI/CD | GitHub Actions | Git events, API calls |

---

## 5. Synchronous vs Asynchronous Boundaries

### Synchronous (request → response, < 1 second)

- All REST API CRUD operations
- Model metadata queries
- Experiment status queries
- Configuration reads/writes
- Health checks
- Cost lookups (cached)

### Asynchronous (task-based, seconds to hours)

- Benchmark execution (minutes per trial)
- Optimization loops (minutes to hours)
- Model download and conversion (minutes)
- Infrastructure provisioning (minutes)
- Deployment rollouts (minutes)
- Quality evaluation (minutes)

### Continuous (background processes)

- Metrics collection (every 10s scrape interval)
- Health monitoring (every 30s)
- Performance degradation detection (every 60s)
- Cost recalculation (hourly)

### Event-Driven Triggers

| Event | Triggers |
|-------|----------|
| Benchmark trial completed | Result recording → next trial selection |
| All trials completed | Quality evaluation → cost analysis → selection |
| Configuration selected | Deployment initiation |
| Deployment completed | Health verification → monitoring activation |
| Performance degradation detected | Re-optimization trigger |
| Model uploaded | Validation → registry update |

---

## 6. Error Handling Strategy

### Error Categories

| Category | Examples | Strategy |
|----------|----------|----------|
| **Transient** | Network timeout, cloud API throttle, temporary DNS failure | Exponential backoff, max 5 retries |
| **Infrastructure** | Instance terminated, disk full, OOM | Clean up, provision new resource, retry operation |
| **Configuration** | Invalid model format, unsupported runtime | Fail fast, return detailed error, no retry |
| **Partial failure** | 3/10 benchmark trials fail | Record failures, continue with successful results, flag in report |
| **Data corruption** | Incomplete metrics, truncated model file | Checksum validation, re-download/re-run |
| **External service** | Cloud API down, HuggingFace unavailable | Circuit breaker, queue for retry, alert |

### State Recovery

All long-running operations (optimization loops, benchmarks, deployments) persist state to the database at each checkpoint. On restart:

1. Query for incomplete operations.
2. Determine last successful checkpoint.
3. Resume from checkpoint or restart the current step.

### Error Propagation

- Worker errors are recorded in the database with full context (traceback, inputs, timestamps).
- API returns structured error responses with error codes and actionable messages.
- Frontend displays errors with context and suggested remediation.
- CLI exits with non-zero status and prints structured error output.

---

## 7. Security Boundaries

### Authentication & Authorization

- **API**: JWT-based authentication. API keys for programmatic access (CLI, CI/CD).
- **Frontend**: OAuth 2.0 / OIDC login flow.
- **Inter-service**: mTLS for gRPC between services. Shared secrets for Celery workers.
- **Cloud credentials**: Never stored in database. Loaded from environment variables or secret manager (AWS Secrets Manager / HashiCorp Vault).

### Network Boundaries

```
┌──────────────────────────────────────────────────┐
│ Public Zone                                       │
│   Frontend (static assets via CDN)                │
│   Backend API (behind load balancer + WAF)        │
│   CLI (client-side, authenticates via API key)    │
└──────────────────────┬───────────────────────────┘
                       │ HTTPS only
┌──────────────────────▼───────────────────────────┐
│ Private Zone (VPC)                                │
│   All backend services                            │
│   Database (PostgreSQL, Redis)                    │
│   Task workers (Celery)                           │
│   Kubernetes control plane                        │
└──────────────────────┬───────────────────────────┘
                       │ VPC peering / private endpoints
┌──────────────────────▼───────────────────────────┐
│ Compute Zone (isolated per experiment)            │
│   Arm64 benchmark instances                       │
│   Inference service pods                          │
│   Metrics exporters                               │
└──────────────────────────────────────────────────┘
```

### Secrets Management

| Secret | Storage | Rotation |
|--------|---------|----------|
| Cloud provider credentials | Environment / Secret Manager | 90-day rotation |
| Database passwords | Environment / Secret Manager | 90-day rotation |
| API signing keys | Environment / Secret Manager | Annual |
| User API keys | Database (hashed) | User-controlled |
| TLS certificates | cert-manager (Kubernetes) | Auto-renewed |

---

## 8. Configuration Strategy

### Configuration Hierarchy (lowest to highest priority)

1. **Default values** — hardcoded sensible defaults in code
2. **Configuration file** — `armserve.toml` in project root
3. **Environment variables** — `ARMSERVE_*` prefix
4. **Database runtime config** — for dynamic configuration
5. **CLI flags** — override everything for that invocation

### Configuration Categories

| Category | Source | Examples |
|----------|--------|----------|
| **Infrastructure** | Terraform variables + env | Cloud region, instance types, VPC CIDR |
| **Application** | `armserve.toml` + env | Database URL, Redis URL, log level |
| **Optimization** | Database + API | Search space bounds, optimization budget, constraints |
| **Experiment** | API request | Model, target metrics, quality thresholds |
| **Secrets** | Environment / Secret Manager | Cloud credentials, API keys, DB passwords |

---

## 9. Deployment Architecture

### Development

- All services run locally via `docker compose`.
- PostgreSQL, Redis, and TimescaleDB in containers.
- Backend API with hot-reload.
- Frontend dev server with HMR.
- No cloud resources required (benchmarks run against local inference).

### Staging

- Kubernetes cluster with Arm64 node pool (single provider).
- Full service deployment via Helm charts.
- Isolated database instances.
- Limited cloud compute budget for benchmark validation.

### Production

- Multi-provider Kubernetes clusters (AWS EKS with Graviton, optionally Azure/GCP).
- PostgreSQL via managed service (RDS/Cloud SQL).
- Redis via managed service (ElastiCache/MemoryStore).
- Grafana + Prometheus stack for monitoring.
- CDN for frontend static assets.
- Load balancer with TLS termination.

---

## 10. Cross-References

- [Component Details](./components.md)
- [Data Flow](./data-flow.md)
- [Deployment Architecture](./deployment.md)
- [Security Model](./security.md)
- [Testing Strategy](./testing.md)
- [Architecture Decision Records](../decisions/)
- [REST API Specification](../api/rest-api.md)
- [gRPC Service Definitions](../api/grpc-services.md)
- [Phase 1 Plan](../development/phase-1-plan.md)
