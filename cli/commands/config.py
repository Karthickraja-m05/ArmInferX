"""ArmServe CLI Config Command Sub-App."""

import json
from pathlib import Path
from typing import Any, Optional

import typer
from dotenv import dotenv_values

from cli.client import ArmServeClient, CLIError
from cli.config import CLIConfig
from cli.formatting import print_config_validation_results, print_error, print_json_output

config_app = typer.Typer(
    name="config",
    help="Manage and validate ArmServe configuration settings.",
    no_args_is_help=True,
)


@config_app.command(name="validate")
def config_validate_command(
    file_to_validate: Optional[Path] = typer.Option(
        None, "--config-file", "-f", help="Path to config file (.env or .json) to validate"
    ),
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
        None, "--config", "-c", help="Path to CLI configuration file"
    ),
) -> None:
    """Validate system configuration against backend validation rules."""
    cfg = CLIConfig.load(
        config_path=config_file,
        api_url=api_url,
        api_key=api_key,
        timeout=timeout,
        json_output=json_output,
    )

    env_overrides: dict[str, Any] | None = None

    if file_to_validate:
        if not file_to_validate.exists():
            print_error(f"Configuration file not found: '{file_to_validate}'")
            raise typer.Exit(code=1)

        try:
            if file_to_validate.suffix == ".json":
                with file_to_validate.open("r", encoding="utf-8") as f:
                    env_overrides = json.load(f)
            else:
                # Treat as .env file
                parsed = dotenv_values(file_to_validate)
                env_overrides = {k: v for k, v in parsed.items() if v is not None}
        except Exception as err:
            print_error(f"Failed to parse config file '{file_to_validate}': {err}")
            raise typer.Exit(code=1) from err

    client = ArmServeClient(cfg)
    try:
        data = client.validate_config(env_overrides=env_overrides)
        if cfg.json_output:
            print_json_output(data)
        else:
            print_config_validation_results(data)

        if not data.get("valid", False):
            raise typer.Exit(code=1)
    except CLIError as err:
        print_error(err.message, details=err.details)
        raise typer.Exit(code=1) from err
    finally:
        client.close()
