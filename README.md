# ArmServe

> Autonomous AI Inference Optimization and Deployment Platform for Arm64 Cloud Infrastructure

ArmServe automates model optimization, benchmark execution, quality evaluation, cost analysis, and production deployment on real Arm64 compute instances (AWS Graviton, Azure Cobalt 100, GCP Axion).

---

## Developer Quickstart

### Prerequisites

- **Python**: 3.10+ (pinned `.python-version`: 3.11.8)
- **Node.js**: 20+ (pinned `.nvmrc`: v20.11.1)
- **Docker**: (Optional for local supporting services) Docker & Docker Compose

### 1. Environment Setup

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

### 2. Install Dependencies

#### Backend & CLI
```bash
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

#### Frontend
```bash
cd frontend
npm install
cd ..
```

---

## Development Workflows

### Run Supporting Services (PostgreSQL + TimescaleDB, Redis)

```bash
docker compose up -d postgres redis
```

### Run Backend API

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```
Open API docs at: [http://localhost:8000/docs](http://localhost:8000/docs)

### Run Frontend Console

```bash
cd frontend
npm run dev
```
Open web UI at: [http://localhost:5173](http://localhost:5173)

---

## Code Quality & Verification

```bash
# Run pytest backend test suite
pytest

# Run Python linting & formatting checks
ruff check backend/ cli/
ruff format --check backend/ cli/

# Run Python static type checking
mypy backend/ cli/

# Run Frontend tests, linting, formatting, & type checks
cd frontend
npm run test
npm run lint
npm run format
npm run type-check
```

---

## Complete Developer Documentation

See [docs/development/setup.md](docs/development/setup.md) for full architecture details, task runners, and Docker service configurations.
