"""ArmServe CLI main entry point."""

from typing import Optional

import typer

from cli.commands.benchmark import benchmark_app
from cli.commands.config import config_app
from cli.commands.experiment import experiment_app
from cli.commands.health import health_command
from cli.commands.system import system_app
from cli.formatting import get_console

__version__ = "0.1.0"

app = typer.Typer(
    name="armserve",
    help="ArmServe CLI — Autonomous AI Inference Optimization Platform for Arm64 Infrastructure.",
    add_completion=False,
)

# Register Sub-Apps (Command Groups)
app.add_typer(system_app, name="system")
app.add_typer(config_app, name="config")
app.add_typer(benchmark_app, name="benchmark")
app.add_typer(experiment_app, name="experiment")

# Register Top-Level Commands
app.command(name="health", help="Check ArmServe backend system health status.")(health_command)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        get_console().print(f"[bold blue]ArmServe CLI[/bold blue] v{__version__}")
        raise typer.Exit(code=0)


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        is_flag=True,
        flag_value=True,
        help="Show ArmServe CLI version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """ArmServe Command Line Interface."""
    if ctx.invoked_subcommand is None and not version:
        get_console().print(ctx.get_help())
        raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
