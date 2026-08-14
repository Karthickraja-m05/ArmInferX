"""ArmServe CLI benchmark command group."""

import httpx
import typer
from rich.table import Table

from cli.formatting import get_console, print_error, print_json_output

benchmark_app = typer.Typer(
    name="benchmark",
    help="Execute, inspect, compare, and report production performance benchmark workloads.",
)


@benchmark_app.command(name="run", help="Run real inference performance benchmark workload.")
def benchmark_run(
    url: str = typer.Option(
        "http://127.0.0.1:8000/api/v1", "--url", "-u", help="ArmServe API base URL."
    ),
    iterations: int = typer.Option(
        10, "--iterations", "-i", help="Number of benchmark iterations."
    ),
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
        table = Table(
            title="ArmServe Production Benchmark Run Summary",
            title_style="bold magenta",
            show_header=True,
        )
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


@benchmark_app.command(
    name="compare", help="Compare two benchmark runs and compute metric variations."
)
def benchmark_compare(
    run_a: str = typer.Argument(..., help="Baseline Benchmark Run ID (Run A)."),
    run_b: str = typer.Argument(..., help="Candidate Benchmark Run ID (Run B)."),
    url: str = typer.Option(
        "http://127.0.0.1:8000/api/v1", "--url", "-u", help="ArmServe API base URL."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON response."),
) -> None:
    """Compare two benchmark runs and compute metric variations."""
    target_url = f"{url.rstrip('/')}/benchmarks/compare?run_a_id={run_a}&run_b_id={run_b}"

    try:
        with httpx.Client(timeout=30.0) as client:
            res = client.post(target_url)
            res.raise_for_status()
            data = res.json()

        if json_output:
            print_json_output(data)
            return

        console = get_console()
        verdict = data.get("verdict", "NEUTRAL")
        verdict_color = (
            "bold red"
            if verdict == "REGRESSED"
            else "bold green"
            if verdict == "IMPROVED"
            else "bold yellow"
        )

        table = Table(
            title=f"ArmServe Performance Comparison: Baseline ({data.get('run_a_id')}) vs Candidate ({data.get('run_b_id')})",
            title_style="bold blue",
            show_header=True,
        )
        table.add_column("Metric", style="cyan")
        table.add_column("Run A (Baseline)", style="dim")
        table.add_column("Run B (Candidate)", style="bold white")
        table.add_column("Abs Diff", style="yellow")
        table.add_column("% Diff", style="magenta")
        table.add_column("Direction / Status", style="bold")

        for item in data.get("comparisons", []):
            dir_str = item.get("direction", "UNCHANGED")
            style = (
                "bold green"
                if dir_str == "IMPROVED"
                else "bold red"
                if dir_str == "REGRESSED"
                else "dim"
            )
            table.add_row(
                f"{item.get('metric_name')} ({item.get('unit')})",
                str(item.get("run_a_value")),
                str(item.get("run_b_value")),
                f"{item.get('absolute_difference'):+}",
                f"{item.get('percentage_difference'):+}%",
                f"[{style}]{dir_str}[/{style}]",
            )

        console.print(table)
        console.print(f"\nOverall Comparison Verdict: [{verdict_color}]{verdict}[/{verdict_color}]")
        for note in data.get("summary_notes", []):
            console.print(f"  • {note}", style="italic dim")

    except Exception as err:
        print_error(f"Benchmark comparison failed: {err}")
        raise typer.Exit(code=1) from err


@benchmark_app.command(
    name="report", help="Generate and print benchmark report in Markdown, JSON, or CSV format."
)
def benchmark_report(
    run_id: str = typer.Argument(..., help="Target Benchmark Run ID."),
    format: str = typer.Option(
        "markdown", "--format", "-f", help="Output report format (markdown, json, csv)."
    ),
    url: str = typer.Option(
        "http://127.0.0.1:8000/api/v1", "--url", "-u", help="ArmServe API base URL."
    ),
) -> None:
    """Generate and print benchmark report."""
    target_url = f"{url.rstrip('/')}/benchmarks/{run_id}/report?format={format}"

    try:
        with httpx.Client(timeout=30.0) as client:
            res = client.get(target_url)
            res.raise_for_status()
            print(res.text)
    except Exception as err:
        print_error(f"Failed to generate benchmark report: {err}")
        raise typer.Exit(code=1) from err


@benchmark_app.command(name="list", help="List historical benchmark run manifests.")
def benchmark_list(
    url: str = typer.Option(
        "http://127.0.0.1:8000/api/v1", "--url", "-u", help="ArmServe API base URL."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON response."),
) -> None:
    """List historical benchmark run manifests."""
    target_url = f"{url.rstrip('/')}/benchmarks"

    try:
        with httpx.Client(timeout=30.0) as client:
            res = client.get(target_url)
            res.raise_for_status()
            data = res.json()

        if json_output:
            print_json_output(data)
            return

        console = get_console()
        table = Table(
            title="ArmServe Historical Benchmark Manifests",
            title_style="bold cyan",
            show_header=True,
        )
        table.add_column("Run ID", style="bold yellow")
        table.add_column("Timestamp", style="dim")
        table.add_column("Requests", style="white")
        table.add_column("Throughput (RPS)", style="bold green")
        table.add_column("P50 Latency", style="magenta")
        table.add_column("Peak RAM", style="cyan")

        for run in data:
            table.add_row(
                str(run.get("run_id")),
                str(run.get("timestamp")),
                str(run.get("total_requests")),
                f"{run.get('requests_per_second')} req/s",
                f"{run.get('latency_p50_ms')} ms",
                f"{run.get('peak_memory_mb')} MB",
            )

        console.print(table)

    except Exception as err:
        print_error(f"Failed to list benchmark runs: {err}")
        raise typer.Exit(code=1) from err
