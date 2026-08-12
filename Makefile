.PHONY: help install dev-services dev-backend dev-frontend test lint format type-check clean ci-local

help:
	@echo "ArmServe Development Task Runner"
	@echo "--------------------------------"
	@echo "make install         - Install backend and frontend dependencies"
	@echo "make dev-services    - Start Docker supporting services (PostgreSQL, Redis)"
	@echo "make dev-backend     - Run FastAPI backend server locally"
	@echo "make dev-frontend    - Run React Vite frontend server locally"
	@echo "make test            - Run backend and frontend test suites"
	@echo "make lint            - Run linters (ruff, eslint)"
	@echo "make format          - Format codebase (ruff format, prettier)"
	@echo "make format-check    - Verify formatting without modifying files"
	@echo "make type-check      - Run type checkers (mypy, tsc)"
	@echo "make ci-local        - Run all CI checks locally (matches GitHub Actions)"
	@echo "make clean           - Remove caches and temporary build files"

install:
	python -m pip install --upgrade pip
	pip install -r requirements-dev.txt
	cd frontend && npm install

dev-services:
	docker compose up -d postgres redis

dev-backend:
	uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

# ─── Formatting ─────────────────────────────────────────────────────
format:
	ruff format backend/ cli/
	cd frontend && npm run format

format-check:
	ruff format --check backend/ cli/

# ─── Linting ────────────────────────────────────────────────────────
lint:
	ruff check backend/ cli/
	cd frontend && npm run lint

# ─── Type Checking ──────────────────────────────────────────────────
type-check:
	mypy backend/ cli/
	cd frontend && npm run type-check

# ─── Testing ────────────────────────────────────────────────────────
test:
	pytest
	cd frontend && npm run test

test-unit:
	pytest backend/tests/unit -ra -q --tb=short

test-integration:
	pytest backend/tests/integration -ra -q --tb=short

test-frontend:
	cd frontend && npm run test

# ─── Frontend Build ─────────────────────────────────────────────────
build-frontend:
	cd frontend && npm run build

# ─── Full CI (Local) ────────────────────────────────────────────────
ci-local: format-check lint type-check test-unit test-integration test-frontend build-frontend
	@echo ""
	@echo "All CI checks passed."

# ─── Cleanup ────────────────────────────────────────────────────────
clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
