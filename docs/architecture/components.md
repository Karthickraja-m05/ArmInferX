# ArmServe — Component Specification

This document defines the responsibility, interface, dependencies, and implementation notes for each ArmServe component.

---

## 1. Frontend

### Responsibility
Web-based dashboard for operating ArmServe. Visualizes experiments, benchmarks, deployments, costs, and system health.

### Technology
- React 18 with TypeScript
- Vite build tooling
- Recharts / Nivo for data visualization
- TanStack Query for server state management
- React Router for client-side routing

### Interface
- **Consumes**: Backend REST API (`/api/v1/*`)
- **Consumes**: Backend WebSocket (`/ws/events`) for real-time updates
- **Produces**: User actions (create experiment, trigger deployment, etc.)

### Key Views
| View | Purpose |
|------|---------|
| Dashboard | System overview, active experiments, deployment health |
| Experiments | Create/view/compare optimization experiments |
| Benchmarks | View benchmark results, latency distributions, throughput charts |
| Models | Model registry, upload, format details |
| Deployments | Active deployments, rollback controls, health status |
| Costs | Cost breakdown per model/instance/experiment |
| Infrastructure | Cloud resource status, instance utilization |
| Settings | Configuration, API keys, cloud provider setup |

### Boundaries
- Frontend is a static SPA. No server-side rendering required.
- All business logic lives in the Backend API. Frontend only renders and collects input.
- Frontend never calls cloud APIs directly. All cloud operations go through the Backend.

---

## 2. Backend API

### Responsibility
Central API gateway. Handles authentication, request validation, CRUD operations, and dispatches long-running tasks to workers.

### Technology
- FastAPI (Python 3.11+)
- Pydantic v2 for request/response validation
- SQLAlchemy 2.0 (async) for ORM
- asyncpg for PostgreSQL connection
- Celery for task dispatch

### Interface

**Inbound (serves)**:
- REST API on `/api/v1/*` (JSON over HTTPS)
- WebSocket on `/ws/events` (real-time event stream)

**Outbound (calls)**:
- PostgreSQL (via SQLAlchemy async)
- Redis (via redis-py async — caching, pub/sub for WebSocket fan-out)
- Celery (task dispatch for async operations)

### API Resource Groups
```
/api/v1/
├── auth/           # Login, token refresh, API key management
├── experiments/    # CRUD, start/stop, results
├── models/         # Registry, upload, download, metadata
├── benchmarks/     # Results, comparison, raw metrics
├── deployments/    # Create, status, rollback, health
├── optimization/   # Status, configuration, constraints
├── metrics/        # Query time-series data
├── costs/          # Cost reports, projections
├── infrastructure/ # Cloud resources, instance types
└── system/         # Health, version, configuration
```

### Boundaries
- The Backend API does NOT execute benchmarks, optimizations, or deployments itself.
- It delegates all long-running work to Celery workers.
- It does NOT hold cloud provider credentials in memory longer than needed for a single operation.

---

## 3. Optimization Controller

### Responsibility
Orchestrates the end-to-end optimization lifecycle. Manages the state machine that drives an optimization run from start to completion.

### Technology
- Python module within the backend codebase
- Executes as Celery tasks
- State persisted in PostgreSQL

### State Machine

```
         ┌──────────┐
         │  CREATED  │
         └────┬──────┘
              │ user triggers start
         ┌────▼──────┐
         │ PLANNING  │  Validate inputs, resolve model, define search space
         └────┬──────┘
              │
         ┌────▼──────┐
    ┌───►│ EXPLORING │  Generate candidate configs, dispatch benchmarks
    │    └────┬──────┘
    │         │ trial results arrive
    │    ┌────▼──────┐
    │    │EVALUATING │  Run quality evaluation, compute cost analysis
    │    └────┬──────┘
    │         │
    │         ├──── more budget remaining? ───► yes ──┐
    │         │                                       │
    │         │ no                                    │
    │    ┌────▼──────┐                           ┌────▼──────┐
    │    │ SELECTING │  Pick best config          │  (loop)   │
    │    └────┬──────┘                           └───────────┘
    │         │                                       │
    │         │                                       │
    └─────────┘◄──────────────────────────────────────┘
              │
         ┌────▼──────┐
         │ DEPLOYING │  Deploy selected config to target infrastructure
         └────┬──────┘
              │
         ┌────▼──────────┐
         │ MONITORING    │  Watch for performance degradation
         └────┬──────────┘
              │ degradation detected
         ┌────▼──────────┐
         │ RE-OPTIMIZING │  Trigger new optimization with updated constraints
         └──────────────┘
```

### Interface
- **Receives**: Start commands from API, scheduler triggers, degradation alerts
- **Dispatches to**: Optimization Agent, Benchmark Engine, Quality Evaluation, Cost Analysis, Deployment Manager
- **Reads/writes**: PostgreSQL (experiment state, trial results)

### Boundaries
- The Controller decides WHAT to do next. It does not execute benchmarks or optimizations itself.
- The Controller is the single owner of optimization lifecycle state.

---

## 4. Optimization Agent

### Responsibility
Implements optimization algorithms. Given a search space and evaluation results, proposes the next configuration to evaluate.

### Technology
- Python
- Optuna for Bayesian optimization (TPE sampler)
- Custom multi-objective optimization for Pareto-optimal selection
- Supports: Bayesian, random search, grid search strategies

### Search Space Dimensions

| Dimension | Type | Example Values |
|-----------|------|---------------|
| `runtime` | Categorical | `onnxruntime`, `llamacpp`, `vllm` |
| `quantization` | Categorical | `fp32`, `fp16`, `int8`, `int4` |
| `instance_type` | Categorical | `c7g.xlarge`, `c7g.2xlarge`, `m7g.xlarge` |
| `num_threads` | Integer | 1–64 |
| `batch_size` | Integer | 1–128 |
| `memory_limit_mb` | Integer | 512–65536 |
| `use_arm_neon` | Boolean | true/false |
| `use_arm_sve` | Boolean | true/false |

### Interface
- **Called by**: Optimization Controller (via Celery task)
- **Receives**: Search space definition, completed trial results, optimization objective
- **Returns**: Next configuration(s) to evaluate, or final selection

### Boundaries
- The Agent is stateless between invocations. All state is passed in and returned.
- The Agent does NOT access cloud APIs, databases, or infrastructure directly.

---

## 5. Experiment Manager

### Responsibility
Manages the lifecycle and metadata of experiments and trials. Provides CRUD operations and query capabilities.

### Technology
- Python module
- SQLAlchemy models
- Direct database access

### Data Model

```
Experiment
├── id: UUID
├── name: str
├── status: enum (CREATED, RUNNING, COMPLETED, FAILED, CANCELLED)
├── model_id: FK → Model
├── search_space: JSON
├── constraints: JSON (latency_p99_ms, min_throughput_rps, max_cost_per_1k, min_quality_score)
├── optimization_strategy: str
├── budget: int (max trials)
├── created_at: timestamp
├── updated_at: timestamp
└── trials: List[Trial]

Trial
├── id: UUID
├── experiment_id: FK → Experiment
├── trial_number: int
├── configuration: JSON (the specific config tested)
├── status: enum (PENDING, RUNNING, COMPLETED, FAILED)
├── benchmark_results: JSON
├── quality_results: JSON
├── cost_results: JSON
├── started_at: timestamp
├── completed_at: timestamp
└── error: str (null if successful)
```

### Interface
- **Called by**: Backend API (CRUD), Optimization Controller (state updates)
- **Reads/writes**: PostgreSQL

### Boundaries
- Experiment Manager is a data management layer. It does not execute experiments.
- It enforces data integrity constraints (e.g., cannot start a completed experiment).

---

## 6. Benchmark Engine

### Responsibility
Executes real performance benchmarks against real inference endpoints running on real Arm64 hardware. Collects latency, throughput, memory, and CPU metrics.

### Technology
- Python benchmark runner
- Runs on target Arm64 instances (either via SSH or as a sidecar container)
- Custom load generation (or integration with tools like `wrk2`, `vegeta`, `ghz`)

### Benchmark Protocol

1. Receive benchmark request (model, configuration, target endpoint).
2. Verify target instance is provisioned and inference service is running.
3. Execute warm-up phase (discard results).
4. Execute measurement phase with controlled load.
5. Collect metrics at defined intervals.
6. Compute summary statistics.
7. Return structured results.

### Metrics Collected

| Metric | Unit | Collection Method |
|--------|------|-------------------|
| Latency (p50, p95, p99, max) | milliseconds | Client-side timing |
| Throughput | requests/second | Request count / duration |
| Time to first token (LLMs) | milliseconds | Streaming response timing |
| Tokens per second (LLMs) | tokens/second | Token count / duration |
| Memory RSS | megabytes | `/proc/[pid]/status` or cgroup metrics |
| CPU utilization | percentage | `/proc/stat` or cgroup metrics |
| Model load time | seconds | Timing from cold start |

### Interface
- **Called by**: Optimization Controller (via Celery task)
- **Requires**: Running inference service on target infrastructure
- **Produces**: Structured benchmark results (stored in database)

### Boundaries
- Benchmark Engine does NOT provision infrastructure. It expects infrastructure to be ready.
- Benchmark Engine does NOT start inference services. It expects them to be running.
- Benchmark Engine runs the REAL benchmark. No simulated results.

---

## 7. Inference Service

### Responsibility
Manages the lifecycle of actual AI inference processes. Starts, configures, and monitors inference runtimes on Arm64 hardware.

### Technology
Wraps real inference runtimes:

| Runtime | Use Case | Arm64 Optimization |
|---------|----------|-------------------|
| ONNX Runtime | General ML models (vision, NLP) | Arm NN execution provider, ACL |
| llama.cpp | LLM inference | NEON SIMD, SVE (where available) |
| vLLM | High-throughput LLM serving | PagedAttention, continuous batching |

### Interface
- **Managed by**: Deployment Manager (lifecycle), Benchmark Engine (load target)
- **Exposes**: HTTP/gRPC inference endpoint (model-specific)
- **Health**: `/health` endpoint for readiness/liveness probes

### Configuration Per Instance
```toml
[inference]
runtime = "onnxruntime"       # or "llamacpp", "vllm"
model_path = "/models/resnet50.onnx"
port = 8080
num_threads = 4
batch_size = 1
quantization = "int8"

[inference.arm]
enable_neon = true
enable_sve = false

[inference.memory]
limit_mb = 4096
```

### Boundaries
- Inference Service is a thin management layer around real runtimes.
- It does NOT implement inference itself — it delegates to ONNX Runtime / llama.cpp / vLLM.
- **PENDING**: Integration with each runtime requires runtime-specific adapter implementation.

---

## 8. Model Management

### Responsibility
Model registry and lifecycle management. Tracks models, their formats, sizes, and compatibility with runtimes.

### Technology
- Python module
- S3-compatible object storage for model files (AWS S3, MinIO for local dev)
- HuggingFace Hub SDK for model downloads

### Data Model

```
Model
├── id: UUID
├── name: str (e.g., "resnet50", "llama-3-8b")
├── source: str (e.g., "huggingface:meta-llama/Llama-3-8B")
├── format: enum (PYTORCH, ONNX, GGUF, SAFETENSORS)
├── quantization: enum (FP32, FP16, INT8, INT4, NONE)
├── size_bytes: int
├── storage_uri: str (S3 URI)
├── checksum_sha256: str
├── compatible_runtimes: List[str]
├── metadata: JSON (architecture, parameter count, etc.)
├── created_at: timestamp
└── updated_at: timestamp
```

### Operations
| Operation | Sync/Async | Description |
|-----------|-----------|-------------|
| Register model | Sync | Add metadata to registry |
| Download from HuggingFace | Async | Download and store in S3 |
| Convert format | Async | PyTorch → ONNX, ONNX → quantized |
| Validate | Async | Verify model loads correctly in target runtime |
| Delete | Sync | Remove from registry and storage |

### Boundaries
- Model Management does NOT run inference. It only stores and tracks models.
- Model conversion is a real operation using real tools (e.g., `torch.onnx.export`, `optimum`).

---

## 9. Quality Evaluation

### Responsibility
Evaluates the output quality of a model under a specific configuration. Ensures optimization does not degrade model accuracy below acceptable thresholds.

### Technology
- Python module
- Task-specific evaluation: accuracy, F1, BLEU, ROUGE, perplexity
- Reference datasets stored in S3

### Evaluation Protocol

1. Receive evaluation request (model, configuration, inference endpoint, evaluation dataset).
2. Send evaluation inputs to the inference endpoint.
3. Collect outputs.
4. Compare outputs to ground truth using appropriate metric.
5. Return quality score.

### Supported Metrics

| Metric | Model Type | Description |
|--------|-----------|-------------|
| Accuracy | Classification | Correct predictions / total |
| F1 Score | Classification | Harmonic mean of precision and recall |
| BLEU | Text generation | N-gram overlap with reference |
| ROUGE | Summarization | Recall-oriented understudy |
| Perplexity | Language models | Exponentiated cross-entropy |
| Exact Match | QA | Exact string match ratio |
| Custom | Any | User-defined evaluation function |

### Interface
- **Called by**: Optimization Controller (via Celery task)
- **Requires**: Running inference endpoint, evaluation dataset
- **Returns**: Quality score and detailed metrics

### Boundaries
- Quality evaluation runs REAL inference on the target model.
- It does NOT simulate or estimate quality.
- Evaluation datasets must be provided by the user or downloaded from known sources.

---

## 10. Cost Analysis

### Responsibility
Calculates the monetary cost of running inference under a specific configuration. Provides cost comparisons and projections.

### Technology
- Python module
- Cloud provider pricing APIs
- AWS Pricing API, Azure Retail Prices API, GCP Cloud Billing API

### Cost Metrics

| Metric | Unit | Description |
|--------|------|-------------|
| Cost per hour | USD/hr | Instance hourly rate |
| Cost per inference | USD | Instance cost / throughput |
| Cost per 1K tokens | USD (LLMs) | Instance cost / token throughput |
| Monthly projected cost | USD | Based on expected request volume |
| Cost vs. x86 comparison | ratio | Arm64 cost / equivalent x86 cost |

### Interface
- **Called by**: Optimization Controller (after benchmark results)
- **Reads**: Cloud provider pricing (cached, refreshed daily)
- **Reads**: Benchmark results (throughput)
- **Returns**: Cost breakdown and projections

### Boundaries
- Cost data comes from real pricing APIs, not hardcoded tables.
- **PENDING**: Cloud pricing API integration for each provider.
- Pricing data is cached locally with a 24-hour TTL.

---

## 11. Cloud Infrastructure Manager

### Responsibility
Provisions and manages Arm64 compute instances across cloud providers. Handles the complete lifecycle: create, configure, monitor, terminate.

### Technology
- Python with cloud provider SDKs
  - AWS: `boto3` (EC2 Graviton instances)
  - Azure: `azure-mgmt-compute` (Cobalt instances)
  - GCP: `google-cloud-compute` (Axion instances)
- Terraform for declarative resource management (long-lived resources)
- Direct SDK calls for ephemeral benchmark instances

### Supported Instance Families

| Provider | Family | Processor | Use Case |
|----------|--------|-----------|----------|
| AWS | c7g | Graviton3 | Compute-optimized inference |
| AWS | m7g | Graviton3 | General-purpose inference |
| AWS | r7g | Graviton3 | Memory-optimized (large models) |
| Azure | Dpsv6 | Cobalt 100 | General-purpose |
| Azure | Epsv6 | Cobalt 100 | Memory-optimized |
| GCP | t2a | Axion | General-purpose |

### Interface
- **Called by**: Optimization Controller (provision for benchmarks), Deployment Manager (provision for production)
- **Manages**: Cloud provider APIs
- **Returns**: Instance metadata (IP, status, specs)

### Operations

| Operation | Sync/Async | Description |
|-----------|-----------|-------------|
| List available instance types | Sync | Query provider for Arm64 options |
| Provision instance | Async | Launch instance, wait for ready |
| Terminate instance | Async | Shut down and clean up |
| Get instance status | Sync | Query current state |
| Estimate cost | Sync | Look up pricing |

### Boundaries
- All provisioning operates on REAL cloud resources.
- **PENDING**: Cloud provider account configuration and credential setup.
- Ephemeral instances are tagged with `armserve:experiment:{id}` for tracking and cleanup.
- A background cleanup job terminates orphaned instances older than the configured TTL (default 2 hours).

---

## 12. Deployment Manager

### Responsibility
Deploys optimized inference configurations to production Kubernetes infrastructure. Manages deployment lifecycle, health verification, and rollback.

### Technology
- Python + official Kubernetes client (`kubernetes` package)
- Generates Kubernetes manifests (Deployment, Service, HPA, ConfigMap)
- Blue/green deployment strategy

### Deployment Protocol

1. Receive deployment request (selected configuration, target cluster).
2. Build inference container image (or select pre-built).
3. Generate Kubernetes manifests from configuration.
4. Apply manifests to cluster (blue/green: deploy new alongside old).
5. Run health checks against new deployment.
6. If healthy: switch traffic, terminate old deployment.
7. If unhealthy: rollback, alert.

### Data Model

```
Deployment
├── id: UUID
├── experiment_id: FK → Experiment
├── trial_id: FK → Trial (the selected trial)
├── configuration: JSON
├── status: enum (PENDING, DEPLOYING, VERIFYING, ACTIVE, ROLLING_BACK, ROLLED_BACK, FAILED)
├── cluster: str
├── namespace: str
├── kubernetes_resources: JSON (generated manifests)
├── health_check_results: JSON
├── previous_deployment_id: FK → Deployment (for rollback chain)
├── created_at: timestamp
└── updated_at: timestamp
```

### Interface
- **Called by**: Optimization Controller (after selection), API (manual deployment)
- **Manages**: Kubernetes API
- **Requires**: Kubernetes cluster access, container registry access

### Boundaries
- Deployment Manager applies REAL Kubernetes manifests to REAL clusters.
- It does NOT simulate deployment success.
- **PENDING**: Kubernetes cluster provisioning and configuration.

---

## 13. Metrics Collection

### Responsibility
Collects, stores, and serves performance metrics from inference services, benchmarks, and infrastructure.

### Technology
- Prometheus for metrics scraping and alerting rules
- TimescaleDB (PostgreSQL extension) for long-term metrics storage
- Custom Python collectors for inference-specific metrics
- Prometheus push gateway for batch job metrics (benchmarks)

### Metrics Schema

```sql
-- TimescaleDB hypertable
CREATE TABLE metrics (
    time        TIMESTAMPTZ NOT NULL,
    source      TEXT NOT NULL,       -- e.g., 'benchmark', 'inference', 'system'
    source_id   UUID,                -- experiment_id, deployment_id, etc.
    metric_name TEXT NOT NULL,       -- e.g., 'latency_p99_ms', 'throughput_rps'
    value       DOUBLE PRECISION NOT NULL,
    labels      JSONB                -- additional dimensions
);

SELECT create_hypertable('metrics', 'time');
```

### Interface
- **Producers**: Benchmark Engine, Inference Service, system exporters (node_exporter)
- **Consumers**: Backend API (queries), Optimization Controller (evaluation), Frontend (visualization)
- **Protocol**: Prometheus scrape (pull), push gateway (push), SQL queries (read)

### Boundaries
- All metrics represent REAL measurements from REAL systems.
- No synthetic or estimated metrics.
- Retention policy: raw data 30 days, 1-minute aggregates 1 year, 1-hour aggregates indefinite.

---

## 14. Observability

### Responsibility
Provides centralized logging, distributed tracing, and alerting across all ArmServe components.

### Technology

| Concern | Technology | Protocol |
|---------|-----------|----------|
| Structured logging | `structlog` (Python) | JSON to stdout → log aggregator |
| Distributed tracing | OpenTelemetry SDK | OTLP to collector |
| Metrics dashboards | Grafana | Prometheus data source + TimescaleDB |
| Alerting | Grafana Alerting / Alertmanager | Webhook, email, Slack |
| Log aggregation | Loki (or ELK) | Push from Promtail/Fluentd |

### Log Format
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "level": "info",
  "logger": "armserve.benchmark.engine",
  "message": "Benchmark trial completed",
  "experiment_id": "550e8400-e29b-41d4-a716-446655440000",
  "trial_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "duration_s": 45.2,
  "latency_p99_ms": 12.3,
  "throughput_rps": 850
}
```

### Trace Context
All inter-service calls propagate OpenTelemetry trace context. A single optimization run generates a trace tree:
```
optimization_run
├── plan_search_space
├── trial_1
│   ├── provision_instance
│   ├── deploy_inference
│   ├── run_benchmark
│   ├── evaluate_quality
│   └── analyze_cost
├── trial_2
│   └── ...
├── select_best
└── deploy_production
```

### Boundaries
- Observability is a cross-cutting concern. Every component emits structured logs and traces.
- No component silently swallows errors.

---

## 15. Database

### Responsibility
Persistent storage for all ArmServe data. Three storage engines serve different access patterns.

### Technology

| Engine | Purpose | Access Pattern |
|--------|---------|---------------|
| PostgreSQL 16 | Application data (experiments, models, deployments, users) | CRUD, transactions, complex queries |
| TimescaleDB | Time-series metrics | Time-range queries, aggregations, downsampling |
| Redis 7 | Task queue broker, caching, pub/sub | Key-value, queues, pub/sub |

### PostgreSQL Schema (Core Tables)

```
models              -- Model registry
experiments         -- Optimization experiments
trials              -- Individual benchmark trials within experiments
configurations      -- Tested configurations (runtime, quantization, etc.)
deployments         -- Production deployments
deployment_history  -- Rollback chain
cloud_resources     -- Provisioned infrastructure
cost_records        -- Cost data per trial/deployment
quality_results     -- Quality evaluation results
api_keys            -- Hashed API keys
audit_log           -- All state changes
```

### Migrations
- Alembic for PostgreSQL schema migrations.
- Migrations are version-controlled and applied automatically on deployment.
- Every migration has a corresponding rollback.

### Redis Usage
| Key Pattern | Purpose | TTL |
|-------------|---------|-----|
| `celery:*` | Task queue (broker + result backend) | Task-dependent |
| `cache:pricing:*` | Cloud pricing data cache | 24 hours |
| `cache:model_meta:*` | Model metadata cache | 1 hour |
| `ws:events:*` | WebSocket event pub/sub | None (ephemeral) |
| `lock:*` | Distributed locks for concurrent operations | 30 seconds |

### Boundaries
- PostgreSQL is the source of truth for all application state.
- TimescaleDB is the source of truth for all time-series metrics.
- Redis is ephemeral. No critical data stored only in Redis.

---

## 16. CLI

### Responsibility
Command-line interface for all ArmServe operations. Designed for automation, scripting, and CI/CD integration.

### Technology
- Python with Typer (based on Click)
- Rich for terminal output formatting
- httpx for API calls

### Command Structure
```
armserve
├── auth
│   ├── login               # Interactive login
│   └── configure            # Set API key
├── experiment
│   ├── create               # Create new experiment
│   ├── list                 # List experiments
│   ├── show <id>            # Show experiment details
│   ├── start <id>           # Start optimization
│   ├── stop <id>            # Stop optimization
│   └── results <id>         # Show results
├── model
│   ├── add                  # Register a model
│   ├── list                 # List models
│   ├── download <source>    # Download from HuggingFace/URL
│   └── delete <id>          # Remove model
├── benchmark
│   ├── run                  # Run standalone benchmark
│   └── results <id>         # Show benchmark results
├── deploy
│   ├── create               # Deploy a configuration
│   ├── list                 # List deployments
│   ├── status <id>          # Deployment status
│   └── rollback <id>        # Rollback deployment
├── cost
│   ├── report               # Generate cost report
│   └── compare              # Compare configurations
├── infra
│   ├── list-instances       # List available Arm64 instance types
│   └── status               # Infrastructure status
└── system
    ├── health               # System health check
    └── version              # Version info
```

### Interface
- Calls Backend REST API exclusively.
- Authenticates via API key stored in `~/.armserve/config.toml`.

### Boundaries
- CLI is a thin client. No business logic.
- CLI does NOT access databases or cloud APIs directly.

---

## 17. Infrastructure-as-Code

### Responsibility
Defines and manages all cloud infrastructure required by ArmServe using declarative configuration.

### Technology
- Terraform 1.6+
- Provider-specific modules (aws, azurerm, google)

### Module Structure
```
infra/
├── modules/
│   ├── networking/       # VPC, subnets, security groups
│   ├── kubernetes/       # EKS/AKS/GKE cluster with Arm64 node pools
│   ├── database/         # RDS PostgreSQL, ElastiCache Redis
│   ├── storage/          # S3 buckets for models
│   ├── monitoring/       # Prometheus, Grafana, Loki
│   └── compute/          # Standalone Arm64 instances (for benchmarks)
├── environments/
│   ├── dev/
│   ├── staging/
│   └── production/
├── variables.tf
├── outputs.tf
└── backend.tf            # Remote state configuration
```

### Boundaries
- Terraform manages REAL cloud resources.
- State is stored remotely (S3 + DynamoDB for locking).
- All infrastructure changes go through plan → review → apply workflow.
- **PENDING**: Provider-specific module implementations.

---

## 18. CI/CD

### Responsibility
Automated build, test, and deployment pipelines.

### Technology
- GitHub Actions

### Pipelines

| Pipeline | Trigger | Steps |
|----------|---------|-------|
| PR Check | Pull request | Lint, type check, unit tests, integration tests |
| Main Build | Push to main | Build, test, build Docker images, push to registry |
| Release | Git tag | Build, test, publish packages, deploy to staging |
| Infrastructure | Changes in `infra/` | Terraform plan, require approval, apply |
| Nightly | Cron (daily) | Full integration test suite, dependency audit |

### Docker Build
- Multi-architecture builds (amd64 + arm64) using `docker buildx`.
- Separate Dockerfiles for backend, frontend, CLI, and inference runtimes.
- Base images: `python:3.11-slim` (backend), `node:20-slim` (frontend build), `nginx:alpine` (frontend serve).

### Boundaries
- CI/CD runs REAL tests against REAL services (in test environment).
- No mocked CI pipelines that always pass.
