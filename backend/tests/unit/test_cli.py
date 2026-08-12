"""Unit tests for ArmServe CLI commands, client, and configuration management."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from cli.client import ArmServeClient
from cli.config import CLIConfig
from cli.main import app

runner = CliRunner()


def test_cli_version_flag() -> None:
    """Verify `armserve --version` displays CLI version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "ArmServe CLI v0.1.0" in result.output


def test_cli_help_menu() -> None:
    """Verify `armserve --help` displays expected subcommands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "health" in result.output
    assert "system" in result.output
    assert "config" in result.output


def test_cli_config_precedence(tmp_path: Path) -> None:
    """Verify CLI configuration option precedence."""
    config_json = tmp_path / "config.json"
    config_json.write_text(json.dumps({"api_url": "http://file-url:8000/api/v1", "timeout": 15.0}))

    cfg = CLIConfig.load(
        config_path=config_json,
        api_url="http://override-url:8000/api/v1",
        timeout=5.0,
    )
    assert cfg.api_url == "http://override-url:8000/api/v1"
    assert cfg.timeout == 5.0

    cfg_file = CLIConfig.load(config_path=config_json)
    assert cfg_file.api_url == "http://file-url:8000/api/v1"
    assert cfg_file.timeout == 15.0


def test_cli_client_headers() -> None:
    """Verify ArmServeClient populates auth headers when api_key is provided."""
    cfg = CLIConfig(api_url="http://test:8000/api/v1", api_key="secret-token-123")
    client = ArmServeClient(cfg)
    assert client.client.headers["X-API-Key"] == "secret-token-123"
    assert client.client.headers["Authorization"] == "Bearer secret-token-123"
    client.close()


@patch.object(ArmServeClient, "get_health")
def test_armserve_health_success(mock_get_health: MagicMock) -> None:
    """Verify `armserve health` on healthy response."""
    mock_get_health.return_value = {
        "status": "healthy",
        "environment": "development",
        "database": "connected",
        "timestamp": "2026-08-12T20:00:00Z",
    }
    result = runner.invoke(app, ["health"])
    assert result.exit_code == 0
    assert "HEALTHY" in result.output
    assert "connected" in result.output


@patch.object(ArmServeClient, "get_health")
def test_armserve_health_degraded_nonzero_exit(mock_get_health: MagicMock) -> None:
    """Verify `armserve health` exits non-zero when status is degraded."""
    mock_get_health.return_value = {
        "status": "degraded",
        "environment": "production",
        "database": "disconnected",
    }
    result = runner.invoke(app, ["health"])
    assert result.exit_code == 1


@patch.object(ArmServeClient, "get_health")
def test_armserve_health_json_flag(mock_get_health: MagicMock) -> None:
    """Verify `armserve health --json` outputs valid JSON."""
    mock_get_health.return_value = {
        "status": "healthy",
        "environment": "test",
        "database": "connected",
    }
    result = runner.invoke(app, ["health", "--json"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["status"] == "healthy"


@patch.object(ArmServeClient, "get_system_info")
def test_armserve_system_info_success(mock_get_info: MagicMock) -> None:
    """Verify `armserve system info` command output."""
    mock_get_info.return_value = {
        "app_name": "ArmServe API",
        "version": "0.1.0",
        "environment": "development",
        "api_version": "v1",
        "python_version": "3.10.11",
        "platform": "Linux",
        "architecture": "aarch64",
        "database_dialect": "postgresql",
        "runtimes_supported": ["onnxruntime"],
        "observability_enabled": True,
    }
    result = runner.invoke(app, ["system", "info"])
    assert result.exit_code == 0
    assert "ArmServe API" in result.output
    assert "aarch64" in result.output


@patch.object(ArmServeClient, "validate_config")
def test_armserve_config_validate_success(mock_validate: MagicMock) -> None:
    """Verify `armserve config validate` command on valid config."""
    mock_validate.return_value = {
        "valid": True,
        "environment": "development",
        "errors": [],
        "config_summary": {"app_env": "development", "debug": True},
    }
    result = runner.invoke(app, ["config", "validate"])
    assert result.exit_code == 0
    assert "PASSED" in result.output


@patch.object(ArmServeClient, "validate_config")
def test_armserve_config_validate_failure(mock_validate: MagicMock) -> None:
    """Verify `armserve config validate` exits non-zero on validation failure."""
    mock_validate.return_value = {
        "valid": False,
        "environment": "production",
        "errors": ["ARMSERVE_DEBUG cannot be True in production environment"],
        "config_summary": {},
    }
    result = runner.invoke(app, ["config", "validate"])
    assert result.exit_code == 1
    assert "FAILED" in result.output


def test_armserve_unreachable_api_failure() -> None:
    """Verify non-zero exit code when API is unreachable."""
    result = runner.invoke(
        app, ["health", "--api-url", "http://localhost:59999/api/v1", "--timeout", "1.0"]
    )
    assert result.exit_code == 1
    assert "timed out" in result.output or "Failed to connect" in result.output
