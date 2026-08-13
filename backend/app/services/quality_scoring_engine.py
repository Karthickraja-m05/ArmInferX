"""ArmServe Automated Quality Scoring Engine.

Evaluates response collection records using exact match, keyword overlap, AST syntax parsing,
and dimension weighting (correctness, completeness, instruction following, formatting consistency).
"""

import ast
import json
from pathlib import Path
import re
import time
from typing import Any

import structlog
from pydantic import BaseModel, Field

from backend.app.services.quality_response_collector import EvaluationCollectionRecord, ResponseItem

logger = structlog.get_logger("backend.app.services.quality_scoring_engine")

EVALUATIONS_DIR = Path("storage/quality/evaluations")


class PromptQualityScore(BaseModel):
    prompt_id: str
    category: str
    correctness_score: float  # [0.0, 100.0]
    completeness_score: float
    instruction_score: float
    formatting_score: float
    total_prompt_score: float  # [0.0, 100.0]
    passed: bool
    evaluation_logs: list[str]


class DimensionWeights(BaseModel):
    correctness: float = 0.35
    completeness: float = 0.25
    instruction_following: float = 0.20
    formatting_consistency: float = 0.20


class QualityEvaluationReport(BaseModel):
    evaluation_id: str
    collection_id: str
    config_id: str
    experiment_id: str
    timestamp: str
    overall_quality_score: float  # [0.0, 100.0]
    passed: bool
    category_scores: dict[str, float]
    dimension_scores: dict[str, float]
    prompt_scores: list[PromptQualityScore]


class QualityScoringEngine:
    """Production Automated Response Quality Scoring Engine."""

    def __init__(self, target_dir: Path | None = None) -> None:
        self.target_dir = target_dir or EVALUATIONS_DIR
        self.target_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _evaluate_single_prompt(item: ResponseItem, weights: DimensionWeights) -> PromptQualityScore:
        """Evaluate accuracy, formatting, completeness, and instruction following for a single response."""
        logs: list[str] = []
        if item.status == "ERROR" or not item.response_text.strip():
            return PromptQualityScore(
                prompt_id=item.prompt_id,
                category=item.category,
                correctness_score=0.0,
                completeness_score=0.0,
                instruction_score=0.0,
                formatting_score=0.0,
                total_prompt_score=0.0,
                passed=False,
                evaluation_logs=[f"Prompt execution failed: {item.error_message or 'Empty output'}"],
            )

        resp_text = item.response_text.strip()
        exp = item.expected_behavior or {}

        # 1. Correctness (Keywords & Exact Match)
        corr_acc = 100.0
        kw_list = exp.get("expected_keywords", [])
        if kw_list:
            found_kw = sum(1 for kw in kw_list if kw.lower() in resp_text.lower())
            corr_acc = (found_kw / len(kw_list)) * 100.0
            logs.append(f"Keyword match: {found_kw}/{len(kw_list)} keywords present ({corr_acc:.1f}%)")

        exact_contains = exp.get("exact_match_contains", [])
        if exact_contains:
            found_exact = sum(1 for term in exact_contains if term.lower() in resp_text.lower())
            exact_acc = (found_exact / len(exact_contains)) * 100.0
            corr_acc = (corr_acc + exact_acc) / 2.0
            logs.append(f"Exact match containment: {found_exact}/{len(exact_contains)} matches ({exact_acc:.1f}%)")

        # 2. Completeness (Non-empty, length check)
        comp_acc = 100.0
        if len(resp_text) < 10:
            comp_acc = 30.0
            logs.append("Warning: Response text length < 10 chars")
        else:
            logs.append(f"Completeness verified: {item.completion_tokens} tokens generated")

        # 3. Instruction Following (Negative constraints / sentence counts)
        inst_acc = 100.0
        max_sentences = exp.get("max_sentence_count")
        if max_sentences:
            sentences = [s for s in re.split(r"[.!?]+", resp_text) if s.strip()]
            if len(sentences) > max_sentences:
                inst_acc = 70.0
                logs.append(f"Instruction limit exceeded: {len(sentences)} sentences (max allowed: {max_sentences})")
            else:
                logs.append("Instruction sentence limit respected")

        # 4. Formatting Consistency (Syntax checks, code blocks, JSON)
        fmt_acc = 100.0
        syntax_check = exp.get("syntax_check")
        if syntax_check == "python":
            # Check python syntax
            try:
                code_match = re.search(r"```python(.*?)```", resp_text, re.DOTALL)
                code_to_parse = code_match.group(1) if code_match else resp_text
                ast.parse(code_to_parse)
                logs.append("Python AST syntax check passed")
            except Exception as syntax_err:
                fmt_acc = 50.0
                logs.append(f"Python AST syntax error: {syntax_err}")
        elif exp.get("format") == "json":
            try:
                json.loads(resp_text)
                logs.append("JSON formatting check passed")
            except Exception:
                fmt_acc = 50.0
                logs.append("JSON formatting check failed")

        total = (
            corr_acc * weights.correctness
            + comp_acc * weights.completeness
            + inst_acc * weights.instruction_following
            + fmt_acc * weights.formatting_consistency
        )

        total_score = round(total, 2)
        passed = total_score >= 70.0

        return PromptQualityScore(
            prompt_id=item.prompt_id,
            category=item.category,
            correctness_score=round(corr_acc, 2),
            completeness_score=round(comp_acc, 2),
            instruction_score=round(inst_acc, 2),
            formatting_score=round(fmt_acc, 2),
            total_prompt_score=total_score,
            passed=passed,
            evaluation_logs=logs,
        )

    def evaluate_collection_record(
        self,
        record: EvaluationCollectionRecord,
        weights: DimensionWeights | None = None,
        min_pass_score: float = 75.0,
    ) -> QualityEvaluationReport:
        """Score entire response collection record across all categories and dimensions."""
        w = weights or DimensionWeights()
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        eval_id = f"eval-{int(time.time())}"

        prompt_scores: list[PromptQualityScore] = []
        category_map: dict[str, list[float]] = {}

        corr_sum, comp_sum, inst_sum, fmt_sum = 0.0, 0.0, 0.0, 0.0

        for r_item in record.responses:
            pscore = self._evaluate_single_prompt(r_item, w)
            prompt_scores.append(pscore)

            category_map.setdefault(r_item.category, []).append(pscore.total_prompt_score)

            corr_sum += pscore.correctness_score
            comp_sum += pscore.completeness_score
            inst_sum += pscore.instruction_score
            fmt_sum += pscore.formatting_score

        count = max(1, len(record.responses))

        cat_scores = {cat: round(sum(scores) / len(scores), 2) for cat, scores in category_map.items()}

        dim_scores = {
            "correctness": round(corr_sum / count, 2),
            "completeness": round(comp_sum / count, 2),
            "instruction_following": round(inst_sum / count, 2),
            "formatting_consistency": round(fmt_sum / count, 2),
        }

        overall_score = round(sum(ps.total_prompt_score for ps in prompt_scores) / count, 2)
        passed = overall_score >= min_pass_score

        report = QualityEvaluationReport(
            evaluation_id=eval_id,
            collection_id=record.collection_id,
            config_id=record.config_id,
            experiment_id=record.experiment_id,
            timestamp=now_str,
            overall_quality_score=overall_score,
            passed=passed,
            category_scores=cat_scores,
            dimension_scores=dim_scores,
            prompt_scores=prompt_scores,
        )

        # Persist quality evaluation manifest
        out_file = self.target_dir / f"{eval_id}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))

        logger.info("Completed automated quality evaluation", eval_id=eval_id, score=overall_score, passed=passed)
        return report


quality_scoring_engine = QualityScoringEngine()

