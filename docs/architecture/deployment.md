# ArmServe — Deployment Architecture

---

## 1. Environment Topology

### Development (Local)

All services run on the developer's machine via Docker Compose.

```
Developer Machine
├── docker compose up
│   ├── backend        (FastAPI, port 8000, hot-reload)
│   ├── celery-worker  (Celery worker, 2 concurrent tasks)
│   ├── celery-beat    (Celery scheduler)
│   ├── postgres       (PostgreSQL 16 + TimescaleDB, port 5432)
│   ├── redis          (Redis 7, port 6379)
│   ├── prometheus     (port 9090)
│   └── grafana        (port 3000)
└── npm run dev
    └── frontend       (Vite dev server, port 5173)
```

**No cloud resources required.** Benchmarks in dev run against a local inference process for validation.

### Staging

Single-cloud deployment (AWS) for integration testing.

```
AWS Account (staging)
├── VPC (10.0.0.0/16)
│   ├── Public Subnets
│   │   ├── ALB (Application Load Balancer)
│   │   └── NAT Gateway
│   ├── Private Subnets
│   │   ├── EKS Cluster
│   │   │   ├── System node group (t3.medium, x86)
│   │   │   │   ├── backend-api
│   │   │   │   ├── celery-worker
│   │   │   │   ├── celery-beat
│   │   │   │   ├── prometheus
│   │   │   │   ├── grafana
│   │   │   │   └── frontend (nginx)
│   │   │   └── Arm64 node group (c7g.xlarge, Graviton)
│   │   │       ├── inference-service pods
│   │   │       └── benchmark-runner pods
│   │   ├── RDS PostgreSQL (db.t3.medium)
│   │   ├── ElastiCache Redis (cache.t3.micro)
│   │   └── S3 Bucket (model storage)
│   └── Security Groups
│       ├── alb-sg (80, 443 from 0.0.0.0/0)
│       ├── app-sg (8000 from alb-sg)
│       ├── db-sg (5432 from app-sg)
│       └── redis-sg (6379 from app-sg)
└── ECR (container images)
```

### Production

Multi-availability-zone deployment. Optionally multi-cloud.

```
AWS Account (production)
├── VPC (10.1.0.0/16)
│   ├── 3 Availability Zones
│   ├── Public Subnets (3x)
│   │   ├── ALB (cross-AZ)
│   │   ├── CloudFront CDN (frontend static assets)
│   │   └── NAT Gateways (3x)
│   ├── Private Subnets (3x)
│   │   ├── EKS Cluster
│   │   │   ├── System node group (m5.large x3, multi-AZ)
│   │   │   │   ├── backend-api (3 replicas)
│   │   │   │   ├── celery-worker (3 replicas)
│   │   │   │   ├── celery-beat (1 replica, leader election)
│   │   │   │   ├── prometheus (1 replica + persistent volume)
│   │   │   │   ├── grafana (1 replica)
│   │   │   │   └── frontend (2 replicas, nginx)
│   │   │   ├── Arm64 inference node group (c7g.2xlarge, auto-scaling)
│   │   │   │   └── inference-service pods (HPA)
│   │   │   └── Arm64 benchmark node group (spot instances, auto-scaling)
│   │   │       └── benchmark-runner pods (scale-to-zero)
│   │   ├── RDS PostgreSQL (db.r6g.large, Multi-AZ, Graviton)
│   │   ├── ElastiCache Redis (cache.r6g.large, cluster mode)
│   │   └── S3 Bucket (model storage, versioning enabled)
│   └── Security Groups (same pattern as staging)
├── ECR (container images)
├── Route 53 (DNS)
├── ACM (TLS certificates)
└── CloudWatch (backup monitoring)
```

---

## 2. Kubernetes Resource Architecture

### Namespace Layout

```
armserve-system        # Core platform services
├── backend-api        # FastAPI deployment
├── celery-worker      # Celery worker deployment
├── celery-beat        # Celery beat deployment
└── frontend           # Nginx serving React SPA

armserve-monitoring    # Observability stack
├── prometheus
├── grafana
├── loki
└── alertmanager

armserve-inference     # Inference workloads (Arm64 nodes only)
├── inference-*        # Dynamically created inference deployments
└── benchmark-*        # Benchmark job pods

armserve-data          # Stateful services (if self-hosted)
├── postgresql
└── redis
```

### Key Kubernetes Resources

```yaml
# Backend API
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-api
  namespace: armserve-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend-api
  template:
    spec:
      containers:
      - name: api
        image: <registry>/armserve-api:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "1000m"
            memory: "1Gi"
        livenessProbe:
          httpGet:
            path: /api/v1/system/health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /api/v1/system/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: armserve-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: armserve-secrets
              key: redis-url
```

```yaml
# Inference Service (Arm64 nodes)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference-{experiment-id}
  namespace: armserve-inference
spec:
  replicas: 1
  template:
    spec:
      nodeSelector:
        kubernetes.io/arch: arm64
      tolerations:
      - key: "arm64"
        operator: "Equal"
        value: "true"
        effect: "NoSchedule"
      containers:
      - name: inference
        image: <registry>/armserve-inference:latest
        resources:
          requests:
            cpu: "4"
            memory: "8Gi"
          limits:
            cpu: "8"
            memory: "16Gi"
        volumeMounts:
        - name: model-volume
          mountPath: /models
      initContainers:
      - name: model-loader
        image: <registry>/armserve-model-loader:latest
        # Downloads model from S3 to shared volume
        volumeMounts:
        - name: model-volume
          mountPath: /models
      volumes:
      - name: model-volume
        emptyDir:
          sizeLimit: 50Gi
```

---

## 3. Container Image Architecture

| Image | Base | Contents | Architecture |
|-------|------|----------|-------------|
| `armserve-api` | `python:3.11-slim` | Backend API + dependencies | amd64, arm64 |
| `armserve-worker` | `python:3.11-slim` | Celery workers + dependencies | amd64, arm64 |
| `armserve-frontend` | `nginx:1.25-alpine` | Built React SPA | amd64, arm64 |
| `armserve-cli` | `python:3.11-slim` | CLI tool | amd64, arm64 |
| `armserve-inference-onnx` | `ubuntu:22.04` | ONNX Runtime + Arm optimizations | arm64 only |
| `armserve-inference-llama` | `ubuntu:22.04` | llama.cpp + Arm NEON/SVE | arm64 only |
| `armserve-inference-vllm` | `python:3.11-slim` | vLLM | arm64 only |
| `armserve-benchmark` | `python:3.11-slim` | Benchmark runner + load tools | arm64 only |
| `armserve-model-loader` | `python:3.11-slim` | S3 download utility | amd64, arm64 |

### Build Strategy

```
docker buildx create --use
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t <registry>/armserve-api:latest \
  --push \
  -f docker/Dockerfile.api .
```

---

## 4. Network Architecture

```
Internet
    │
    ▼
┌──────────────┐
│   CDN        │ ← Frontend static assets (HTML, JS, CSS)
│ (CloudFront) │
└──────┬───────┘
       │
┌──────▼───────┐
│    ALB       │ ← TLS termination, path-based routing
│              │   /api/* → backend-api
│              │   /ws/*  → backend-api (WebSocket upgrade)
│              │   /*     → frontend (nginx)
└──────┬───────┘
       │
┌──────▼───────────────────────────────────────────┐
│              Kubernetes Cluster                   │
│                                                   │
│   ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │
│   │ frontend│  │ backend │  │ celery-worker   │ │
│   │ (nginx) │  │   api   │  │                 │ │
│   └─────────┘  └────┬────┘  └────────┬────────┘ │
│                      │               │           │
│                      ▼               ▼           │
│                ┌──────────┐   ┌───────────┐      │
│                │  Redis   │   │PostgreSQL │      │
│                └──────────┘   └───────────┘      │
│                                                   │
│   ┌─────────────────────────────────────────┐    │
│   │  Arm64 Node Pool                        │    │
│   │  ┌───────────┐  ┌───────────────────┐   │    │
│   │  │ inference │  │ benchmark-runner │   │    │
│   │  │  service  │  │     (Job)        │   │    │
│   │  └───────────┘  └───────────────────┘   │    │
│   └─────────────────────────────────────────┘    │
└──────────────────────────────────────────────────┘
```

---

## 5. Scaling Strategy

| Component | Scaling | Trigger |
|-----------|---------|---------|
| Backend API | HPA (horizontal) | CPU > 70%, request latency > 500ms |
| Celery Workers | HPA | Queue depth > 10 tasks |
| Frontend | HPA | CPU > 70% |
| Inference Service | Per-deployment HPA | Request latency, queue depth |
| Benchmark Runner | Job-based | One pod per benchmark trial |
| PostgreSQL | Vertical (instance size) | Connection count, CPU |
| Redis | Vertical + cluster mode | Memory usage, connection count |
| Arm64 Node Pool | Cluster Autoscaler | Pending pods |

---

## 6. Backup and Recovery

| Data | Backup Method | Frequency | Retention |
|------|--------------|-----------|-----------|
| PostgreSQL | RDS automated snapshots | Daily | 30 days |
| PostgreSQL (critical) | pg_dump to S3 | Every 6 hours | 90 days |
| Model artifacts (S3) | S3 versioning + cross-region replication | Continuous | Indefinite |
| Terraform state | S3 versioning | On every apply | 90 days |
| Grafana dashboards | JSON export to Git | On change | Indefinite |
| Redis | Not backed up (ephemeral by design) | N/A | N/A |

### Recovery Time Objectives

| Scenario | RTO | RPO |
|----------|-----|-----|
| Database failure | 15 minutes (RDS failover) | 0 (Multi-AZ sync) |
| Application crash | 2 minutes (K8s restart) | 0 |
| Full cluster failure | 30 minutes (Terraform recreate) | 6 hours (last pg_dump) |
| Model storage failure | 1 hour (cross-region restore) | 0 (versioning) |
