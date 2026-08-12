# ArmServe PowerShell Task Runner for Windows
param (
    [Parameter(Mandatory=$true)]
    [string]$Task
)

switch ($Task) {
    "install" {
        python -m pip install --upgrade pip
        pip install -r requirements-dev.txt
        Set-Location frontend
        cmd /c npm install
        Set-Location ..
    }
    "dev-services" {
        docker compose up -d postgres redis
    }
    "dev-backend" {
        uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
    }
    "dev-frontend" {
        Set-Location frontend
        cmd /c npm run dev
        Set-Location ..
    }
    "test" {
        pytest
        Set-Location frontend
        cmd /c npm run test
        Set-Location ..
    }
    "lint" {
        ruff check backend/ cli/
        Set-Location frontend
        cmd /c npm run lint
        Set-Location ..
    }
    "format" {
        ruff format backend/ cli/
        Set-Location frontend
        cmd /c npm run format
        Set-Location ..
    }
    "type-check" {
        mypy backend/ cli/
        Set-Location frontend
        cmd /c npm run type-check
        Set-Location ..
    }
    Default {
        Write-Host "Unknown task: $Task. Available: install, dev-services, dev-backend, dev-frontend, test, lint, format, type-check"
    }
}
