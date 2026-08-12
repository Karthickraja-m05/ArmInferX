# ArmServe Developer Setup Guide

This document details the local environment setup, task runner options, testing procedures, and code quality tools.

---

## 1. Toolchain & Tool Versions

| Component | Pinned Version | Configuration File |
|-----------|----------------|--------------------|
| **Python** | `3.11.8` | `.python-version` |
| **Node.js** | `v20.11.1` | `.nvmrc` |
| **Backend Package** | `setuptools` | `pyproject.toml`, `requirements-dev.txt` |
| **Frontend Package** | `npm` | `frontend/package.json` |
| **Python Formatter & Linter** | `ruff 0.3.2` | `pyproject.toml` (`[tool.ruff]`) |
| **Python Type Checker** | `mypy 1.9.0` | `pyproject.toml` (`[tool.mypy]`) |
| **Python Test Runner** | `pytest 8.1.1` | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Frontend Linter & Formatter** | `eslint 8.57.0`, `prettier 3.2.5` | `frontend/.eslintrc.json`, `frontend/.prettierrc` |
| **Frontend Type Checker** | `tsc 5.2.2` | `frontend/tsconfig.json` |

---

## 2. Windows PowerShell Commands

For Windows developers without `make`:

```powershell
# Install Python and Frontend dependencies
.\tasks.ps1 -Task install

# Run backend unit and integration tests
.\tasks.ps1 -Task test

# Run linter checks
.\tasks.ps1 -Task lint

# Run type checker
.\tasks.ps1 -Task type-check
```

---

## 3. Directory Layout

```
ArmInferX/
├── .editorconfig
├── .env.example
├── .gitignore
├── .nvmrc
├── .python-version
├── Makefile
├── pyproject.toml
├── README.md
├── requirements-dev.txt
├── requirements.txt
├── tasks.ps1
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers
│   │   ├── core/         # Config, logging, DB
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic data validation
│   │   ├── services/     # Business logic
│   │   └── main.py       # ASGI entry point
│   └── tests/            # Pytest test suite
├── cli/                  # Typer CLI application
├── docker/               # Docker configs (Prometheus, etc.)
├── docs/                 # Architecture, ADRs, & API specifications
└── frontend/             # React + Vite TypeScript SPA
```
