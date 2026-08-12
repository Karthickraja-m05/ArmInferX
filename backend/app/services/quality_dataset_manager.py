"""ArmServe Quality Evaluation Dataset Management Engine.

Manages, persists, and versions evaluation datasets across categories (reasoning,
summarization, coding, question answering, classification) independent of evaluation code.
"""

import json
from pathlib import Path
import time
from typing import Any, Literal

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger("backend.app.services.quality_dataset_manager")

DATASETS_DIR = Path("storage/datasets")


class PromptItem(BaseModel):
    prompt_id: str
    prompt: str
    category: Literal["reasoning", "summarization", "coding", "question_answering", "classification"]
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    expected_behavior: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DatasetManifest(BaseModel):
    dataset_id: str
    name: str
    version: str = "1.0.0"
    created_at: str
    prompts: list[PromptItem]


class QualityDatasetManager:
    """Production Evaluation Dataset Repository & Versioning Manager."""

    def __init__(self, target_dir: Path | None = None) -> None:
        self.target_dir = target_dir or DATASETS_DIR
        self.target_dir.mkdir(parents=True, exist_ok=True)
        self._seed_default_datasets_if_empty()

    def _seed_default_datasets_if_empty(self) -> None:
        """Seed initial versioned evaluation datasets if directory is empty."""
        if list(self.target_dir.glob("*.json")):
            return

        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ")

        default_prompts = [
            PromptItem(
                prompt_id="p-reasoning-1",
                prompt="If all cats are mammals and all mammals are animals, are all cats animals?",
                category="reasoning",
                difficulty="easy",
                expected_behavior={"expected_keywords": ["yes", "cats are animals"], "format": "text"},
            ),
            PromptItem(
                prompt_id="p-coding-1",
                prompt="Write a Python function named `is_palindrome(s: str) -> bool` that checks if a string is a palindrome.",
                category="coding",
                difficulty="medium",
                expected_behavior={"expected_keywords": ["def is_palindrome", "return"], "syntax_check": "python"},
            ),
            PromptItem(
                prompt_id="p-qa-1",
                prompt="What is the capital of France?",
                category="question_answering",
                difficulty="easy",
                expected_behavior={"exact_match_contains": ["Paris"]},
            ),
            PromptItem(
                prompt_id="p-summary-1",
                prompt="Summarize the following in one sentence: ArmServe is an autonomous AI optimization platform designed for AWS Graviton ARM64 CPU inference infrastructure.",
                category="summarization",
                difficulty="easy",
                expected_behavior={"max_sentence_count": 1, "expected_keywords": ["ArmServe", "ARM64"]},
            ),
            PromptItem(
                prompt_id="p-class-1",
                prompt="Classify the sentiment of this text as POSITIVE or NEGATIVE: 'The performance tuning on Graviton servers produced incredible throughput gains.'",
                category="classification",
                difficulty="easy",
                expected_behavior={"exact_match_contains": ["POSITIVE"]},
            ),
        ]

        manifest = DatasetManifest(
            dataset_id="eval-core-v1",
            name="ArmServe Core Benchmark Evaluation Dataset",
            version="1.0.0",
            created_at=now_str,
            prompts=default_prompts,
        )

        out_file = self.target_dir / "eval-core-v1.json"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(manifest.model_dump_json(indent=2))

        logger.info("Seeded default quality evaluation dataset", dataset_id="eval-core-v1", count=len(default_prompts))

    def save_dataset(self, manifest: DatasetManifest) -> Path:
        """Persist dataset manifest to disk."""
        out_file = self.target_dir / f"{manifest.dataset_id}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(manifest.model_dump_json(indent=2))
        return out_file

    def get_dataset(self, dataset_id: str = "eval-core-v1") -> DatasetManifest | None:
        """Retrieve dataset manifest by ID."""
        file_path = self.target_dir / f"{dataset_id}.json"
        if not file_path.exists():
            matches = list(self.target_dir.glob(f"*{dataset_id}*.json"))
            if not matches:
                return None
            file_path = matches[0]

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
            return DatasetManifest(**data)

    def list_datasets(self) -> list[DatasetManifest]:
        """List all managed dataset manifests."""
        datasets = []
        for f in self.target_dir.glob("*.json"):
            try:
                with open(f, encoding="utf-8") as f_in:
                    datasets.append(DatasetManifest(**json.load(f_in)))
            except Exception:
                pass
        return datasets
