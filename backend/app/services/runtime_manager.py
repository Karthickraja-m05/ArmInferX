"""ArmServe Runtime & Model Lifecycle Manager.

Manages model loading, unloading, reloading, state transitions, runtime health, and metadata persistence.
"""

from enum import Enum
import json
from pathlib import Path
import time
from typing import Any

import structlog

from backend.app.services.inference_engine import engine, MODEL_PATH
from backend.app.services.model_downloader import ensure_model_available

logger = structlog.get_logger("backend.app.services.runtime_manager")

MODELS_DIR = Path("storage/models")


class ModelLifecycleState(str, Enum):
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ERROR = "error"


class RuntimeManager:
    """Manages active inference model lifecycle and runtime health."""

    def __init__(self):
        self.active_model_id: str | None = "qwen2.5-0.5b-instruct"
        self.state: ModelLifecycleState = ModelLifecycleState.LOADED if engine.loaded else ModelLifecycleState.UNLOADED
        self.last_state_change: str = time.strftime("%Y-%m-%dT%H:%M:%SZ")

    def get_runtime_status(self) -> dict[str, Any]:
        """Return runtime health status and active model telemetry."""
        return {
            "status": "healthy" if self.state == ModelLifecycleState.LOADED else "degraded",
            "engine": "ArmServe-GGUF-MLAS",
            "architecture": "aarch64",
            "active_model_id": self.active_model_id,
            "lifecycle_state": self.state.value,
            "last_state_change": self.last_state_change,
            "engine_loaded": engine.loaded,
            "tensors_count": len(engine.reader.tensors) if engine.reader else 0,
            "fields_count": len(engine.reader.fields) if engine.reader else 0,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    def discover_models(self) -> list[dict[str, Any]]:
        """Discover all registered models and metadata in storage/models."""
        ensure_model_available()
        models = []
        for meta_file in MODELS_DIR.glob("*.json"):
            try:
                with open(meta_file, encoding="utf-8") as f:
                    meta = json.load(f)
                    m_id = meta.get("id", meta_file.stem)
                    meta["is_active"] = (m_id == self.active_model_id and self.state == ModelLifecycleState.LOADED)
                    models.append(meta)
            except Exception as err:
                logger.error("Failed to read model metadata", file=str(meta_file), error=str(err))

        if not models:
            models.append({
                "id": "qwen2.5-0.5b-instruct",
                "name": "Qwen2.5-0.5B-Instruct GGUF",
                "version": "2.5-0.5b",
                "quantization": "Q4_K_M",
                "format": "gguf",
                "is_active": self.state == ModelLifecycleState.LOADED,
            })

        return models

    def load_model(self, model_id: str) -> dict[str, Any]:
        """Load target model into runtime memory (unloads active model if needed)."""
        logger.info("Lifecycle Event: Load model requested", model_id=model_id)

        if self.state == ModelLifecycleState.LOADED and self.active_model_id == model_id:
            logger.info("Model already loaded", model_id=model_id)
            return self.get_model_status(model_id)

        # Unload active model if any
        if self.state == ModelLifecycleState.LOADED:
            self.unload_model(self.active_model_id or model_id)

        self.state = ModelLifecycleState.LOADING
        try:
            engine.load_model()
            self.active_model_id = model_id
            self.state = ModelLifecycleState.LOADED
            self.last_state_change = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            logger.info("Lifecycle Event: Model loaded successfully", model_id=model_id)
        except Exception as err:
            self.state = ModelLifecycleState.ERROR
            logger.error("Lifecycle Event: Model load failed", model_id=model_id, error=str(err))
            raise RuntimeError(f"Failed to load model {model_id}: {err}") from err

        return self.get_model_status(model_id)

    def unload_model(self, model_id: str) -> dict[str, Any]:
        """Unload model from runtime memory and free RAM."""
        logger.info("Lifecycle Event: Unload model requested", model_id=model_id)
        engine.loaded = False
        engine.reader = None
        self.state = ModelLifecycleState.UNLOADED
        self.last_state_change = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        logger.info("Lifecycle Event: Model unloaded successfully", model_id=model_id)
        return self.get_model_status(model_id)

    def reload_model(self, model_id: str) -> dict[str, Any]:
        """Reload target model into runtime memory."""
        logger.info("Lifecycle Event: Reload model requested", model_id=model_id)
        self.unload_model(model_id)
        return self.load_model(model_id)

    def get_model_status(self, model_id: str) -> dict[str, Any]:
        """Query model lifecycle status and metadata."""
        is_active = (self.active_model_id == model_id)
        return {
            "model_id": model_id,
            "status": self.state.value if is_active else ModelLifecycleState.UNLOADED.value,
            "is_active": is_active and self.state == ModelLifecycleState.LOADED,
            "last_state_change": self.last_state_change,
            "engine": "ArmServe-GGUF-MLAS",
            "format": "gguf",
        }


# Global runtime manager singleton instance
runtime_manager = RuntimeManager()
