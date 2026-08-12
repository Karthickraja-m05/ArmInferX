# ArmServe — Phase 1 Implementation Plan

## 1. Goal
Establish foundational scaffolding, core database models, REST API skeleton, CLI foundation, and standalone real benchmark execution runner on local/Arm64 compute.

---

## 2. Deliverables Checklist

### Phase 1.1: Environment & Project Scaffolding
- [ ] Initialize Python backend module layout with `pyproject.toml` (Poetry/uv).
- [ ] Setup Docker Compose environment (`PostgreSQL`, `TimescaleDB`, `Redis`).
- [ ] Initialize React frontend boilerplate with Vite and TypeScript.

### Phase 1.2: Core Data Models & Database Migrations
- [ ] Define SQLAlchemy 2.0 async models for `Model`, `Experiment`, `Trial`, `Deployment`.
- [ ] Configure Alembic database migration scripts.
- [ ] Define TimescaleDB hypertable schema for metric ingestion.

### Phase 1.3: Backend API & CLI
- [ ] Implement FastAPI core router & `/system/health` status endpoints.
- [ ] Implement REST CRUD endpoints for `/models` and `/experiments`.
- [ ] Implement Typer CLI skeleton with `armserve experiment create` commands.

### Phase 1.4: Real Benchmark Execution Engine (Local/Arm64 target)
- [ ] Implement Benchmark Engine worker task capable of calling ONNX Runtime CPU endpoints.
- [ ] Collect latency (p50, p95, p99) and throughput metrics from real execution.
- [ ] Store benchmark results in PostgreSQL + TimescaleDB.

---

## 3. Phase 1 Verification Criteria
1. `docker compose up` starts DB, Redis, Backend, and Frontend without errors.
2. `pytest` executes unit and integration tests cleanly.
3. CLI successfully submits a real experiment configuration to Backend API.
4. Celery worker executes a real local ONNX inference benchmark, recording non-zero, empirical execution metrics into PostgreSQL and TimescaleDB.
