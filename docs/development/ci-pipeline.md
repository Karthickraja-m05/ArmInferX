# ArmServe CI Pipeline

This document describes the automated CI pipeline and how to reproduce all checks locally.

## Pipeline Overview

The pipeline runs on **GitHub Actions** for all pull requests and pushes to `main`/`develop`. It consists of 12 parallel checks grouped into 4 categories, plus a final status gate.

### Pipeline Architecture

```
┌────────────────────────────────────────────────────────┐
│                  ArmServe CI Pipeline                  │
│  Trigger: PR to main/develop, push to main/develop     │
├──────────────┬──────────────┬───────────┬──────────────┤
│   Backend    │   Frontend   │   Infra   │  Security    │
├──────────────┼──────────────┼───────────┼──────────────┤
│ 1. Format    │ 6. Lint      │ 9. Format │ 11. Secrets  │
│ 2. Lint      │ 7. Tests     │ 10.Validate│ 12. Deps    │
│ 3. TypeCheck │ 8. Build     │  (3 envs) │              │
│ 4. Unit Tests│              │           │              │
│ 5. Int Tests │              │           │              │
├──────────────┴──────────────┴───────────┴──────────────┤
│                   CI Status Gate                       │
│  Fails if ANY required check above fails               │
└────────────────────────────────────────────────────────┘
```

## CI Checks

| # | Check | Tool | Command | Fails CI? |
|---|-------|------|---------|-----------|
| 1 | Backend formatting | ruff format | `ruff format --check backend/ cli/` | ✅ Yes |
| 2 | Backend linting | ruff check | `ruff check backend/ cli/` | ✅ Yes |
| 3 | Backend type checking | mypy | `mypy backend/ cli/` | ✅ Yes |
| 4 | Backend unit tests | pytest | `pytest backend/tests/unit -ra -q --tb=short` | ✅ Yes |
| 5 | Backend integration tests | pytest | `pytest backend/tests/integration -ra -q --tb=short` | ✅ Yes |
| 6 | Frontend linting | ESLint | `cd frontend && npm run lint` | ✅ Yes |
| 7 | Frontend tests | Vitest | `cd frontend && npm run test` | ✅ Yes |
| 8 | Frontend build | tsc + Vite | `cd frontend && npm run build` | ✅ Yes |
| 9 | IaC formatting | terraform fmt | `terraform fmt -check -recursive infra/` | ✅ Yes |
| 10 | IaC validation | terraform validate | `terraform init -backend=false && terraform validate` (per env) | ✅ Yes |
| 11 | Secret scanning | gitleaks | `gitleaks detect --source . --verbose --no-git` | ✅ Yes |
| 12 | Dependency audit | pip-audit + npm audit | `pip-audit` / `npm audit` | ⚠️ Advisory |

## Reproducing CI Locally

### Prerequisites

```bash
# Python 3.10+ with dev dependencies
pip install -r requirements-dev.txt

# Node 20 with frontend dependencies
cd frontend && npm install && cd ..

# Terraform 1.6+ (optional, for IaC checks)
# Install from https://developer.hashicorp.com/terraform/downloads
```

### Run All Checks (Single Command)

```bash
# Using Make (Linux/macOS/WSL)
make ci-local

# Using PowerShell (Windows)
.\tasks.ps1 ci-local
```

### Run Individual Checks

```bash
# Backend
ruff format --check backend/ cli/     # 1. Format check
ruff check backend/ cli/              # 2. Lint
mypy backend/ cli/                    # 3. Type check
pytest backend/tests/unit -ra -q      # 4. Unit tests
pytest backend/tests/integration -ra -q  # 5. Integration tests

# Frontend
cd frontend
npm run lint                          # 6. ESLint
npm run test                          # 7. Vitest
npm run build                         # 8. Production build

# Infra (requires Terraform CLI)
terraform fmt -check -recursive infra/  # 9. Format check
cd infra/environments/dev
terraform init -backend=false
terraform validate                    # 10. Validation
```

### Auto-Fixing Formatting Issues

```bash
# Backend: auto-format
ruff format backend/ cli/

# Frontend: auto-format
cd frontend && npm run format
```

## Branch Protection

For full CI enforcement, configure GitHub branch protection on `main`:
1. **Settings → Branches → Branch protection rules → Add rule**
2. Pattern: `main`
3. Enable: **Require status checks to pass before merging**
4. Required checks: `CI Status Gate`

This single status gate aggregates all 12 checks — if any required check fails, the PR cannot be merged.
