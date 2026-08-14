"""ArmServe Quality Response Collection Engine.

Executes evaluation dataset prompts against live inference runtime, captures real outputs,
measures latency, and associates response records with target configuration IDs.
"""

import time
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

from backend.app.services.inference_engine import CompletionRequest, InferenceEngine
from backend.app.services.quality_dataset_manager import (
    QualityDatasetManager,
)

logger = structlog.get_logger("backend.app.services.quality_response_collector")

RESPONSES_DIR = Path("storage/quality/responses")


class ResponseItem(BaseModel):
    prompt_id: str
    category: str
    prompt: str
    response_text: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    status: str = "SUCCESS"  # SUCCESS | ERROR
    error_message: str | None = None
    expected_behavior: dict[str, Any] = Field(default_factory=dict)


class EvaluationCollectionRecord(BaseModel):
    collection_id: str
    dataset_id: str
    config_id: str
    experiment_id: str
    timestamp: str
    responses: list[ResponseItem]


class QualityResponseCollector:
    """Production Response Collector for Live Inference Evaluation."""

    def __init__(self, target_dir: Path | None = None) -> None:
        self.target_dir = target_dir or RESPONSES_DIR
        self.target_dir.mkdir(parents=True, exist_ok=True)
        self.dataset_manager = QualityDatasetManager()
        self.inference_engine = InferenceEngine()

    async def collect_dataset_responses(
        self,
        config_id: str,
        experiment_id: str,
        dataset_id: str = "eval-core-v1",
    ) -> EvaluationCollectionRecord:
        """Execute all prompts in target dataset against live inference runtime."""
        dataset = self.dataset_manager.get_dataset(dataset_id)
        if not dataset:
            raise ValueError(f"Dataset '{dataset_id}' not found.")

        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        coll_id = f"coll-{int(time.time())}"
        response_items: list[ResponseItem] = []

        logger.info(
            "Starting dataset response collection",
            config_id=config_id,
            dataset_id=dataset_id,
            count=len(dataset.prompts),
        )

        for item in dataset.prompts:
            t0 = time.time()
            try:
                # Call live inference runtime using CompletionRequest
                req = CompletionRequest(
                    prompt=item.prompt,
                    max_tokens=256,
                    temperature=0.0,
                )
                inf_res = self.inference_engine.generate_completion(req)
                elapsed_ms = round((time.time() - t0) * 1000.0, 2)

                text_out = inf_res["choices"][0]["text"]
                usage = inf_res.get("usage", {})

                response_items.append(
                    ResponseItem(
                        prompt_id=item.prompt_id,
                        category=item.category,
                        prompt=item.prompt,
                        response_text=text_out,
                        latency_ms=elapsed_ms,
                        prompt_tokens=usage.get("prompt_tokens", 0),
                        completion_tokens=usage.get("completion_tokens", 0),
                        status="SUCCESS",
                        expected_behavior=item.expected_behavior,
                    )
                )
            except Exception as err:
                elapsed_ms = round((time.time() - t0) * 1000.0, 2)
                logger.error(
                    "Response collection prompt failure", prompt_id=item.prompt_id, error=str(err)
                )
                response_items.append(
                    ResponseItem(
                        prompt_id=item.prompt_id,
                        category=item.category,
                        prompt=item.prompt,
                        response_text="",
                        latency_ms=elapsed_ms,
                        prompt_tokens=0,
                        completion_tokens=0,
                        status="ERROR",
                        error_message=str(err),
                        expected_behavior=item.expected_behavior,
                    )
                )

        record = EvaluationCollectionRecord(
            collection_id=coll_id,
            dataset_id=dataset_id,
            config_id=config_id,
            experiment_id=experiment_id,
            timestamp=now_str,
            responses=response_items,
        )

        # Persist response collection manifest
        out_file = self.target_dir / f"{coll_id}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(record.model_dump_json(indent=2))

        return record
