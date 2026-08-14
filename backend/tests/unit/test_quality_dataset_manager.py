"""Unit tests for Quality Dataset Manager."""

from pathlib import Path

from backend.app.services.quality_dataset_manager import (
    DatasetManifest,
    PromptItem,
    QualityDatasetManager,
)


def test_quality_dataset_manager_seeding(tmp_path: Path) -> None:
    """Test initial seeding and retrieval of quality evaluation datasets."""
    mgr = QualityDatasetManager(target_dir=tmp_path)
    datasets = mgr.list_datasets()
    assert len(datasets) == 1
    manifest = datasets[0]
    assert manifest.dataset_id == "eval-core-v1"
    assert len(manifest.prompts) >= 5


def test_save_and_get_dataset(tmp_path: Path) -> None:
    """Test persisting and retrieving custom versioned datasets."""
    mgr = QualityDatasetManager(target_dir=tmp_path)

    custom = DatasetManifest(
        dataset_id="eval-custom-v2",
        name="Custom Test Dataset",
        version="2.0.0",
        created_at="2026-08-12T00:00:00Z",
        prompts=[
            PromptItem(
                prompt_id="p-custom-1",
                prompt="Explain gravity in simple terms.",
                category="question_answering",
                difficulty="easy",
            )
        ],
    )

    mgr.save_dataset(custom)
    retrieved = mgr.get_dataset("eval-custom-v2")
    assert retrieved is not None
    assert retrieved.name == "Custom Test Dataset"
    assert len(retrieved.prompts) == 1
