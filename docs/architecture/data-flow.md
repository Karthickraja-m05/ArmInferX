# ArmServe — Data Flow

This document describes how data moves through the ArmServe platform, covering the primary workflows and their data transformations.

---

## 1. Primary Data Flow: Optimization Run

This is the core workflow — from experiment creation to deployed, optimized configuration.

```
User/CLI                    Backend API                 Workers (Celery)
   │                            │                            │
   │  POST /experiments         │                            │
   │  {model, constraints,      │                            │
   │   search_space, budget}    │                            │
   ├───────────────────────────►│                            │
   │                            │  validate + store          │
   │                            │  in PostgreSQL             │
   │  201 {experiment_id}       │                            │
   │◄───────────────────────────┤                            │
   │                            │                            │
   │  POST /experiments/:id/    │                            │
   │       start                │                            │
   ├───────────────────────────►│                            │
   │                            │  dispatch task             │
   │                            ├───────────────────────────►│
   │  202 {status: starting}    │                            │
   │◄───────────────────────────┤                            │
   │                            │                            │
   │                            │                ┌───────────┤
   │                            │                │ Optimization Controller
   │                            │                │           │
   │                            │                │  1. Resolve model
   │                            │                │  2. Define search space
   │                            │                │  3. Loop:
   │                            │                │     a. Ask Agent for next config
   │                            │                │     b. Provision infrastructure
   │                            │                │     c. Deploy inference service
   │                            │                │     d. Run benchmark
   │                            │                │     e. Evaluate quality
   │                            │                │     f. Analyze cost
   │                            │                │     g. Record results
   │                            │                │     h. Check budget
   │                            │                │  4. Select best config
   │                            │                │  5. Deploy to production
   │                            │                └───────────┤
   │                            │                            │
   │  WebSocket: status updates │◄───────────────────────────┤
   │◄══════════════════════════ │                            │
```

---

## 2. Detailed Trial Execution Data Flow

Each trial within an optimization run follows this sequence:

```
Optimization         Cloud Infra        Inference        Benchmark        Quality
Controller           Manager            Service          Engine           Evaluation
    │                    │                   │                │                │
    │ provision_instance │                   │                │                │
    ├───────────────────►│                   │                │                │
    │                    │ boto3.run_instances()              │                │
    │                    │──────────────►     │                │                │
    │                    │ instance_id, ip    │                │                │
    │ ◄──────────────────┤                   │                │                │
    │                    │                   │                │                │
    │ deploy_inference(config, model, ip)    │                │                │
    ├───────────────────────────────────────►│                │                │
    │                    │                   │ load model     │                │
    │                    │                   │ start server   │                │
    │                    │                   │ health: OK     │                │
    │ ◄─────────────────────────────────────┤                │                │
    │                    │                   │                │                │
    │ run_benchmark(endpoint, params)        │                │                │
    ├───────────────────────────────────────────────────────►│                │
    │                    │                   │                │                │
    │                    │                   │◄── HTTP reqs ──┤                │
    │                    │                   │── responses ──►│                │
    │                    │                   │   (repeated)   │                │
    │                    │                   │                │                │
    │ benchmark_results  │                   │                │                │
    │ {latency_p99: 12ms,│                   │                │                │
    │  throughput: 850rps,                   │                │                │
    │  memory_mb: 2048}  │                   │                │                │
    │ ◄─────────────────────────────────────────────────────┤                │
    │                    │                   │                │                │
    │ evaluate_quality(endpoint, eval_dataset)│                │                │
    ├──────────────────────────────────────────────────────────────────────►│
    │                    │                   │                │                │
    │                    │                   │◄── eval inputs ────────────────┤
    │                    │                   │── predictions ────────────────►│
    │                    │                   │                │                │
    │ quality_results    │                   │                │                │
    │ {accuracy: 0.94,   │                   │                │                │
    │  f1: 0.92}         │                   │                │                │
    │ ◄──────────────────────────────────────────────────────────────────────┤
    │                    │                   │                │                │
    │ terminate_instance │                   │                │                │
    ├───────────────────►│                   │                │                │
    │                    │ boto3.terminate()  │                │                │
    │ ◄──────────────────┤                   │                │                │
    │                    │                   │                │                │
    │ store trial results in PostgreSQL      │                │                │
    │ push metrics to TimescaleDB            │                │                │
```

---

## 3. Data Transformation Pipeline

### Input → Storage → Output

```
User Input                     Stored Data                    Output
──────────                     ───────────                    ──────

Model source URL          →    Model record (PostgreSQL)  →   Model metadata (API)
                               Model file (S3)            →   Model file (Inference)

Experiment config         →    Experiment record           →   Experiment status (API)
                               Trial records               →   Results dashboard (Frontend)
                               Benchmark metrics (TS)      →   Charts, comparisons

Cloud credentials (env)   →    (not stored in DB)         →   Provisioned instances

Benchmark raw data        →    Metrics (TimescaleDB)      →   Aggregated stats (API)
                               Trial.benchmark_results     →   Optimization input

Quality eval outputs      →    Trial.quality_results      →   Quality comparison (API)
                                                           →   Constraint check input

Pricing data (API)        →    Cache (Redis, 24h TTL)     →   Cost per inference (API)
                               Cost records (PostgreSQL)   →   Cost report (Frontend)

Selected configuration    →    Deployment record          →   Running K8s pods
                               K8s manifests               →   Deployment status (API)
```

---

## 4. Real-Time Event Flow

Events flow from workers to the Frontend via WebSocket:

```
Worker (Celery)                 Redis Pub/Sub              Backend API              Frontend
     │                              │                          │                       │
     │ trial.completed              │                          │                       │
     │  {experiment_id,             │                          │                       │
     │   trial_id,                  │                          │                       │
     │   results: {...}}            │                          │                       │
     ├─────────────────────────────►│                          │                       │
     │                              │ channel: events          │                       │
     │                              ├─────────────────────────►│                       │
     │                              │                          │ WebSocket push        │
     │                              │                          ├──────────────────────►│
     │                              │                          │                       │ update UI
     │                              │                          │                       │
```

### Event Types

| Event | Source | Payload |
|-------|--------|---------|
| `experiment.started` | Controller | `{experiment_id}` |
| `trial.started` | Controller | `{experiment_id, trial_id, config}` |
| `trial.benchmark_complete` | Benchmark Engine | `{trial_id, metrics}` |
| `trial.quality_complete` | Quality Eval | `{trial_id, quality_score}` |
| `trial.completed` | Controller | `{trial_id, full_results}` |
| `experiment.selection` | Controller | `{experiment_id, best_trial_id}` |
| `deployment.started` | Deployment Mgr | `{deployment_id}` |
| `deployment.healthy` | Deployment Mgr | `{deployment_id}` |
| `deployment.failed` | Deployment Mgr | `{deployment_id, error}` |
| `alert.degradation` | Monitoring | `{deployment_id, metric, threshold}` |

---

## 5. Metrics Data Flow

```
                          Scrape (pull)                    Query (SQL)
Inference Pod  ─────────────────────►  Prometheus  ──────────────────►  Grafana
   :8080/metrics                        :9090                          :3000
                                          │
                                          │ remote_write
                                          ▼
                                     TimescaleDB  ◄──────────────────  Backend API
                                                     SQL queries        :8000
                                                                          │
                                                                          ▼
                                                                       Frontend

Benchmark Job  ─── push ──►  Push Gateway  ◄── scrape ──  Prometheus
                              :9091                          :9090
```

### Metrics Retention Policy

| Resolution | Retention | Storage |
|-----------|-----------|---------|
| Raw (per-second) | 30 days | TimescaleDB |
| 1-minute aggregates | 1 year | TimescaleDB (continuous aggregate) |
| 1-hour aggregates | Indefinite | TimescaleDB (continuous aggregate) |

---

## 6. Model Lifecycle Data Flow

```
HuggingFace Hub                    ArmServe                        S3 Storage
     │                                │                                │
     │  download request              │                                │
     │◄───────────────────────────────┤                                │
     │                                │                                │
     │  model weights + config        │                                │
     ├───────────────────────────────►│                                │
     │                                │  validate checksum             │
     │                                │  detect format                 │
     │                                │  extract metadata              │
     │                                │                                │
     │                                │  upload to S3                  │
     │                                ├───────────────────────────────►│
     │                                │                                │
     │                                │  record in PostgreSQL          │
     │                                │  {id, name, format, size,      │
     │                                │   storage_uri, checksum,       │
     │                                │   compatible_runtimes}         │
     │                                │                                │
     │                                │                                │
     │                     Later: benchmark needs model                │
     │                                │                                │
     │                                │  download from S3              │
     │                                │◄───────────────────────────────┤
     │                                │  mount into inference container│
```

---

## 7. Deployment Data Flow

```
Optimization          Deployment            Container          Kubernetes
Controller            Manager               Registry           Cluster
     │                    │                      │                  │
     │ deploy(config,     │                      │                  │
     │  trial_id)         │                      │                  │
     ├───────────────────►│                      │                  │
     │                    │                      │                  │
     │                    │ build/select image    │                  │
     │                    ├─────────────────────►│                  │
     │                    │ image digest          │                  │
     │                    │◄─────────────────────┤                  │
     │                    │                      │                  │
     │                    │ generate manifests    │                  │
     │                    │ (Deployment, Service, │                  │
     │                    │  ConfigMap, HPA)      │                  │
     │                    │                      │                  │
     │                    │ kubectl apply (blue)  │                  │
     │                    ├──────────────────────────────────────►│
     │                    │                      │                  │
     │                    │ wait for rollout      │                  │
     │                    │ health check          │                  │
     │                    │◄─────────────────────────── ready ─────┤
     │                    │                      │                  │
     │                    │ switch traffic        │                  │
     │                    │ (update Service)      │                  │
     │                    ├──────────────────────────────────────►│
     │                    │                      │                  │
     │                    │ terminate old (green) │                  │
     │                    ├──────────────────────────────────────►│
     │                    │                      │                  │
     │ deployment_id,     │                      │                  │
     │ status: ACTIVE     │                      │                  │
     │◄───────────────────┤                      │                  │
```

---

## 8. Re-Optimization Trigger Flow

```
Prometheus              Alertmanager           Backend API          Optimization
  :9090                                         :8000               Controller
    │                        │                      │                    │
    │ alert:                 │                      │                    │
    │ latency_p99 > threshold│                      │                    │
    ├───────────────────────►│                      │                    │
    │                        │ webhook POST         │                    │
    │                        ├─────────────────────►│                    │
    │                        │                      │ trigger            │
    │                        │                      │ re-optimization    │
    │                        │                      ├───────────────────►│
    │                        │                      │                    │
    │                        │                      │    new experiment  │
    │                        │                      │    with updated    │
    │                        │                      │    constraints     │
    │                        │                      │    (narrowed       │
    │                        │                      │     search space)  │
    │                        │                      │◄───────────────────┤
```
