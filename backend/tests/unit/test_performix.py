"""Unit tests for Arm Performix integration, correlation, and evidence generator."""

import pytest

from backend.app.schemas.performix import PerformixRunRequest
from backend.app.services.optimization_evidence_generator import evidence_generator
from backend.app.services.performix_comparator import performix_comparator
from backend.app.services.performix_runner import performix_runner


@pytest.mark.asyncio
async def test_performix_runner_and_persistence():
    """Test running real Performix benchmark and persisting manifest."""
    req = PerformixRunRequest(
        model_id="qwen2.5-0.5b-instruct",
        thread_count=4,
        batch_size=16,
        iterations=2,
    )
    result = await performix_runner.run_benchmark(req)

    assert result.performix_run_id.startswith("pmx-")
    assert result.execution_status == "COMPLETED"
    assert result.latency_p50_ms > 0
    assert result.tokens_per_second > 0

    # Retrieve from history
    fetched = performix_runner.get_result(result.performix_run_id)
    assert fetched.performix_run_id == result.performix_run_id


def test_performix_correlation():
    """Test correlating ArmServe benchmark vs Performix benchmark."""
    # Ensure at least one Performix run exists
    history = performix_runner.list_results(limit=1)
    if not history:
        pytest.skip("No Performix history available")

    pmx_id = history[0].performix_run_id
    comp = performix_comparator.compare_runs("bm-run-001", pmx_id)

    assert comp.armserve_run_id == "bm-run-001"
    assert comp.performix_run_id == pmx_id
    assert comp.overall_consistency_score >= 0.0
    assert len(comp.metrics_comparison) == 6


def test_optimization_evidence_generator():
    """Test generating evidence report in Markdown, JSON, and CSV formats."""
    md_report = evidence_generator.generate_report("markdown")
    assert md_report.format == "markdown"
    assert "ArmServe Hackathon Submission" in md_report.content

    json_report = evidence_generator.generate_report("json")
    assert json_report.format == "json"
    assert '"report_id":' in json_report.content

    csv_report = evidence_generator.generate_report("csv")
    assert csv_report.format == "csv"
    assert "P50_Latency_ms" in csv_report.content
