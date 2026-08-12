"""ArmServe CLI Health Command."""

from pathlib import Path
from typing import Optional

import typer

from cli.client import ArmServeClient, CLIError
from cli.config import CLIConfig
from cli.formatting import print_error, print_health_table, print_json_output


def health_command(
    api_url: Optional[str] = typer.Option(
        None, "--api-url", "-u", help="ArmServe Backend API Base URL"
    ),
    api_key: Optional[str] = typer.Option(
        None, "--api-key", "-k", help="API Key / Token for backend auth"
    ),
    json_output: bool = typer.Option(
        False, "--json", flag_value=True, help="Format output as JSON"
    ),
    timeout: Optional[float] = typer.Option(
        None, "--timeout", "-t", help="HTTP request timeout in seconds"
    ),
    config_file: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to custom configuration file"
    ),
) -> None:
    """Check backend system health status."""
    cfg = CLIConfig.load(
        config_path=config_file,
        api_url=api_url,
        api_key=api_key,
        timeout=timeout,
        json_output=json_output,
    )
    client = ArmServeClient(cfg)
    try:
        data = client.get_health()
        if cfg.json_output:
            print_json_output(data)
        else:
            print_health_table(data)

        # Non-zero exit if status is degraded or unhealthy
        if data.get("status") != "healthy":
            raise typer.Exit(code=1)
    except CLIError as err:
        print_error(err.message, details=err.details)
        raise typer.Exit(code=1) from err
    finally:
        client.close()
