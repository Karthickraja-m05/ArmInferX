"""ArmServe CLI experiment command group."""

import json
import httpx
from rich.table import Table
import typer

from cli.formatting import get_console, print_error, print_json_output

experiment_app = typer.Typer(
    name="experiment",
    help="Generate, execute, and track parameter optimization experiments.",
)


@experiment_app.command(name="generate", help="Generate experiment configurations from parameter spec.")
def experiment_generate(
    url: str = typer.Option("http://127.0.0.1:8000/api/v1", "--url", "-u", help="ArmServe API base URL."),
    threads: str = typer.Option("1,2,4", "--threads", "-t", help="Comma-separated thread counts."),
    batch_sizes: str = typer.Option("64,128", "--batch-sizes", "-b", help="Comma-separated batch sizes."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON response."),
) -> None:
    """Generate experiment configurations from parameter spec."""
    target_url = f"{url.rstrip('/')}/experiments/generate"
    try:
        t_list = [int(x.strip()) for x in threads.split(",")]
        b_list = [int(x.strip()) for x in batch_sizes.split(",")]
    except ValueError as err:
        print_error("Invalid integer in threads or batch-sizes spec.")
        raise typer.Exit(code=1) from err

    payload = {
        "thread_counts": t_list,
        "batch_sizes": b_list,
        "context_lengths": [2048],
        "temperatures": [0.0],
        "max_tokens_list": [256],
        "model_id": "qwen2.5-0.5b-instruct",
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            res = client.post(target_url, json=payload)
            res.raise_for_status()
            data = res.json()

        if json_output:
            print_json_output(data)
            return

        console = get_console()
        table = Table(title="Generated Experiment Configurations", title_style="bold green", show_header=True)
        table.add_column("Config ID", style="bold yellow")
        table.add_column("Threads", style="cyan")
        table.add_column("Batch Size", style="magenta")
        table.add_column("Context", style="white")
        table.add_column("Temp", style="dim")
        table.add_column("Signature", style="dim")

        for cfg in data:
            table.add_row(
                str(cfg.get("config_id")),
                str(cfg.get("thread_count")),
                str(cfg.get("batch_size")),
                str(cfg.get("context_length")),
                str(cfg.get("temperature")),
                str(cfg.get("hash_signature")),
            )

        console.print(table)
        console.print(f"\nGenerated [bold green]{len(data)}[/bold green] valid experiment configuration(s).")

    except Exception as err:
        print_error(f"Failed to generate experiment configurations: {err}")
        raise typer.Exit(code=1) from err


@experiment_app.command(name="run", help="Execute an optimization experiment configuration.")
def experiment_run(
    config_id: str = typer.Argument(..., help="Target Configuration ID (e.g. cfg-a1b2c3d4)."),
    url: str = typer.Option("http://127.0.0.1:8000/api/v1", "--url", "-u", help="ArmServe API base URL."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON response."),
) -> None:
    """Execute an optimization experiment configuration."""
    target_url = f"{url.rstrip('/')}/experiments/execute?config_id={config_id}"

    try:
        with httpx.Client(timeout=180.0) as client:
            res = client.post(target_url)
            res.raise_for_status()
            data = res.json()

        if json_output:
            print_json_output(data)
            return

        console = get_console()
        status_str = data.get("status", "UNKNOWN")
        status_color = "bold green" if status_str == "COMPLETED" else "bold red"

        table = Table(title=f"ArmServe Experiment Run Summary — {data.get('experiment_id')}", title_style="bold blue", show_header=True)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="bold white")

        table.add_row("Experiment ID", str(data.get("experiment_id")))
        table.add_row("Config ID", str(data.get("config_id")))
        table.add_row("Status", f"[{status_color}]{status_str}[/{status_color}]")
        table.add_row("Started At", str(data.get("started_at")))
        table.add_row("Completed At", str(data.get("completed_at")))
        table.add_row("Benchmark Run Ref", str(data.get("benchmark_run_id")))

        summary = data.get("metrics_summary") or {}
        if summary:
            table.add_row("Throughput (RPS)", f"{summary.get('requests_per_second')} req/s")
            table.add_row("Tokens Per Second", f"{summary.get('tokens_per_second')} tok/s")
            table.add_row("P50 Latency", f"{summary.get('latency_p50_ms')} ms")
            table.add_row("Peak RAM", f"{summary.get('peak_memory_mb')} MB")

        console.print(table)

    except Exception as err:
        print_error(f"Experiment execution failed: {err}")
        raise typer.Exit(code=1) from err


@experiment_app.command(name="list", help="List historical experiment run manifests.")
def experiment_list(
    url: str = typer.Option("http://127.0.0.1:8000/api/v1", "--url", "-u", help="ArmServe API base URL."),
    status_filter: str = typer.Option(None, "--status", "-s", help="Filter by status (COMPLETED, FAILED)."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON response."),
) -> None:
    """List historical experiment run manifests."""
    target_url = f"{url.rstrip('/')}/experiments"
    if status_filter:
        target_url += f"?status_filter={status_filter}"

    try:
        with httpx.Client(timeout=30.0) as client:
            res = client.get(target_url)
            res.raise_for_status()
            data = res.json()

        if json_output:
            print_json_output(data)
            return

        console = get_console()
        table = Table(title="ArmServe Experiment Execution History", title_style="bold cyan", show_header=True)
        table.add_column("Experiment ID", style="bold yellow")
        table.add_column("Config ID", style="dim")
        table.add_column("Status", style="bold")
        table.add_column("P50 Latency", style="magenta")
        table.add_column("Throughput (RPS)", style="bold green")
        table.add_column("Started At", style="dim")

        for exp in data:
            st = exp.get("status", "UNKNOWN")
            st_color = "bold green" if st == "COMPLETED" else "bold red"
            summary = exp.get("metrics_summary") or {}
            table.add_row(
                str(exp.get("experiment_id")),
                str(exp.get("config_id")),
                f"[{st_color}]{st}[/{st_color}]",
                f"{summary.get('latency_p50_ms', 'N/A')} ms",
                f"{summary.get('requests_per_second', 'N/A')} req/s",
                str(exp.get("started_at")),
            )

        console.print(table)

    except Exception as err:
        print_error(f"Failed to list experiments: {err}")
        raise typer.Exit(code=1) from err
