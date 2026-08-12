"""Integration tests for ArmServe CLI against real backend FastAPI application."""

from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from backend.app.main import app as fastapi_app
from cli.client import ArmServeClient
from cli.config import CLIConfig
from cli.main import app as cli_app

runner = CliRunner()


@pytest.fixture(autouse=True)
def mock_asgi_client() -> Iterator[None]:
    """Patch ArmServeClient to use TestClient targeting real FastAPI app."""
    original_init = ArmServeClient.__init__

    def patched_init(self: ArmServeClient, config: CLIConfig) -> None:
        original_init(self, config)
        self.client = TestClient(fastapi_app, base_url="http://localhost:8000/api/v1")

    with patch.object(ArmServeClient, "__init__", patched_init):
        yield


def test_cli_integration_health() -> None:
    """Verify `armserve health` against real backend FastAPI app."""
    result = runner.invoke(cli_app, ["health"])
    assert result.exit_code == 0
    assert "HEALTHY" in result.stdout
    assert "ArmServe System Health" in result.stdout


def test_cli_integration_system_info() -> None:
    """Verify `armserve system info` against real backend FastAPI app."""
    result = runner.invoke(cli_app, ["system", "info"])
    assert result.exit_code == 0
    assert "ArmServe API" in result.stdout
    assert "0.1.0" in result.stdout
    assert "onnxruntime" in result.stdout


def test_cli_integration_config_validate() -> None:
    """Verify `armserve config validate` against real backend FastAPI app."""
    result = runner.invoke(cli_app, ["config", "validate"])
    assert result.exit_code == 0
    assert "PASSED" in result.stdout
    assert "Active Configuration Summary" in result.stdout


def test_cli_integration_json_formatting() -> None:
    """Verify `--json` flag works end-to-end with real backend API responses."""
    result = runner.invoke(cli_app, ["system", "info", "--json"])
    assert result.exit_code == 0
    assert '"app_name": "ArmServe API"' in result.stdout
