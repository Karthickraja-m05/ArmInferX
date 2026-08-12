"""Formatting and presentation utilities for ArmServe CLI using Rich."""

import json
from typing import Any

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table


def get_console() -> Console:
    """Return a Rich Console bound to current stdout."""
    return Console()


def get_error_console() -> Console:
    """Return a Rich Console bound to current stderr."""
    return Console(stderr=True)


def print_json_output(data: dict[str, Any] | list[Any]) -> None:
    """Print formatted JSON output to console."""
    get_console().print_json(json.dumps(data, indent=2, default=str))


def print_error(message: str, details: Any = None) -> None:
    """Print structured red error panel to stderr."""
    err_console = get_error_console()
    err_console.print(f"[bold red]Error:[/bold red] {escape(message)}")
    if details and isinstance(details, dict | list):
        err_console.print_json(json.dumps(details, indent=2, default=str))


def print_health_table(health_data: dict[str, Any]) -> None:
    """Print system health table."""
    console = get_console()
    status_str = health_data.get("status", "unknown")
    status_style = "bold green" if status_str == "healthy" else "bold red"

    table = Table(title="ArmServe System Health", title_style="bold cyan", show_header=True)
    table.add_column("Property", style="bold white")
    table.add_column("Status / Value")

    table.add_row("Overall Health Status", f"[{status_style}]{status_str.upper()}[/{status_style}]")
    table.add_row("Environment", str(health_data.get("environment", "unknown")))
    table.add_row("Database Connection", str(health_data.get("database", "unknown")))
    table.add_row("Timestamp (UTC)", str(health_data.get("timestamp", "n/a")))

    console.print(table)


def print_system_info_table(info_data: dict[str, Any]) -> None:
    """Print system diagnostics table."""
    console = get_console()
    table = Table(
        title="ArmServe System Information & Diagnostics", title_style="bold blue", show_header=True
    )
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")

    table.add_row("Application Name", str(info_data.get("app_name", "N/A")))
    table.add_row("Application Version", str(info_data.get("version", "N/A")))
    table.add_row("API Version", str(info_data.get("api_version", "N/A")))
    table.add_row("Target Environment", str(info_data.get("environment", "N/A")))
    table.add_row("Python Runtime", str(info_data.get("python_version", "N/A")))
    table.add_row("Host OS Platform", str(info_data.get("platform", "N/A")))
    table.add_row("CPU Architecture", str(info_data.get("architecture", "N/A")))
    table.add_row("Database Dialect", str(info_data.get("database_dialect", "N/A")))
    table.add_row("Supported Runtimes", ", ".join(info_data.get("runtimes_supported", [])))
    table.add_row(
        "Observability Enabled", "Yes" if info_data.get("observability_enabled") else "No"
    )

    console.print(table)


def print_config_validation_results(val_data: dict[str, Any]) -> None:
    """Print configuration validation results."""
    console = get_console()
    is_valid = val_data.get("valid", False)
    status_text = "[bold green]PASSED[/bold green]" if is_valid else "[bold red]FAILED[/bold red]"

    console.print(
        Panel(
            f"Configuration Validation: {status_text}", title="ArmServe Config Check", expand=False
        )
    )

    errors = val_data.get("errors", [])
    if errors:
        console.print("[bold red]Validation Errors Detected:[/bold red]")
        for err in errors:
            console.print(f"  - {escape(str(err))}", style="red")

    summary = val_data.get("config_summary", {})
    if summary:
        table = Table(title="Active Configuration Summary", show_header=True)
        table.add_column("Setting Key", style="dim")
        table.add_column("Value", style="bold yellow")
        for key, val in summary.items():
            table.add_row(key, str(val))
        console.print(table)
