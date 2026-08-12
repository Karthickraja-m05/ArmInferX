"""ArmServe CLI benchmark command group."""

import json
import httpx
from rich.table import Table
import typer

from cli.formatting import get_console, print_error, print_json_output

benchmark_app = typer.Typer(
    name="benchmark",
    help="Execute and inspect production performance benchmark workloads.",
)


@benchmark_app.command(name="run", help="Run real inference performance benchmark workload.")
def benchmark_run(
    url: str = typer.Option("http://127.0.0.1:8000/api/v1", "--url", "-u", help="ArmServe API base URL."),
    iterations: int = typer.Option(10, "--iterations", "-i", help="Number of benchmark iterations."),
    warmup: int = typer.Option(3, "--warmup", "-w", help="Number of warmup iterations."),
    concurrency: int = typer.Option(1, "--concurrency", "-c", help="Concurrency worker level."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON response."),
) -> None:
    """Execute real inference performance benchmark workload."""
    target_url = f"{url.rstrip('/')}/benchmarks/run"
    payload = {
        "model_id": "qwen2.5-0.5b-instruct",
        "warmup_iterations": warmup,
        "iterations": iterations,
        "concurrency": concurrency,
        "prompt": "What ARM64 Neoverse V1 CPU optimizations are used in ArmServe?",
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            res = client.post(target_url, json=payload)
            res.raise_for_status()
            data = res.json()

        if json_output:
            print_json_output(data)
            return

        console = get_console()
        table = Table(title="ArmServe Production Benchmark Run Summary", title_style="bold magenta", show_header=True)
        table.add_column("Benchmark Metric", style="cyan", no_wrap=True)
        table.add_column("Measured Value", style="bold green")

        table.add_row("Run ID", str(data.get("run_id", "N/A")))
        table.add_row("Timestamp", str(data.get("timestamp", "N/A")))
        table.add_row("Total Requests", str(data.get("total_requests")))
        table.add_row("Successful Requests", str(data.get("successful_requests")))
        table.add_row("Duration (sec)", f"{data.get('duration_seconds')} s")
        table.add_row("Throughput (RPS)", f"{data.get('requests_per_second')} req/s")
        table.add_row("Tokens Per Second", f"{data.get('tokens_per_second')} tok/s")
        table.add_row("P50 Latency", f"{data.get('latency_p50_ms')} ms")
        table.add_row("P90 Latency", f"{data.get('latency_p90_ms')} ms")
        table.add_row("P99 Latency", f"{data.get('latency_p99_ms')} ms")
        table.add_row("Peak Memory", f"{data.get('peak_memory_mb')} MB")

        console.print(table)

    except Exception as err:
        print_error(f"Benchmark run failed: {err}")
        raise typer.Exit(code=1) from err
