# ArmServe — Testing Strategy

---

## 1. Multi-Tier Testing Hierarchy

```
       ▲
      / \        E2E System Tests (Real Arm64 Cloud Execution)
     /   \       ----------------------------------------------
    /     \      Integration Tests (API ↔ DB ↔ Redis ↔ Workers)
   /       \     ----------------------------------------------
  /         \    Component Tests (Mocked Cloud SDKs / Runtimes)
 /___________\   ----------------------------------------------
                 Unit Tests (Pure Functions, Algorithms, Parsers)
```

---

## 2. Testing Levels

### Unit Tests
- **Focus**: Optimization algorithms, Optuna trial generation, Pydantic schemas, config validation, cost calculation formulas.
- **Framework**: `pytest` (Python), `vitest` (TypeScript).
- **Execution Target**: Local machine / CI pipelines. Real-time fast feedback (< 30s).

### Component & Integration Tests
- **Focus**: FastAPI endpoints, SQLAlchemy repository layers, Celery task triggers, PostgreSQL schema migrations.
- **Dependencies**: Uses `testcontainers-python` for ephemeral PostgreSQL and Redis instances.
- **Execution Target**: CI / Local Docker Compose environment.

### End-to-End (E2E) Real Infrastructure Tests
- **Focus**: Validation of real benchmark execution, Cloud Infra Manager provisioning on Arm64 hardware, model loading, and metrics collection.
- **Strict Rule**: E2E tests run on real Arm64 compute (e.g. AWS Graviton instance in staging). No mocks permitted in E2E runs.
- **Execution Target**: Scheduled nightly CI trigger or on-demand release candidate workflow.

---

## 3. Test Verification Commands

```bash
# Unit & Fast Integration Tests
pytest tests/unit tests/integration -v

# Static Analysis & Linting
flake8 src/ backend/
mypy backend/
npm run lint --prefix frontend

# Real Infrastructure E2E Suite (Requires Cloud Credentials)
pytest tests/e2e --real-cloud --provider=aws --region=us-east-1
```
