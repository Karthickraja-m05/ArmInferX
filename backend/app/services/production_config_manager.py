"""Production Configuration Manager service for ArmServe.

Handles validation, SHA-256 version hashing, parameter boundary checks,
and configuration diff comparison for production deployments.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Valid parameter bounds for production inference configurations on AWS ARM64
MIN_THREADS = 1
MAX_THREADS = 128
MIN_BATCH_SIZE = 1
MAX_BATCH_SIZE = 1024
MIN_CONTEXT_LENGTH = 128
MAX_CONTEXT_LENGTH = 131072
MIN_TEMPERATURE = 0.0
MAX_TEMPERATURE = 2.0


class ProductionRuntimeConfigSchema(BaseModel):
    """Pydantic schema for strict production runtime configuration validation."""

    model_id: str = Field(..., description="Model key or path identifier")
    thread_count: int = Field(..., ge=MIN_THREADS, le=MAX_THREADS)
    batch_size: int = Field(..., ge=MIN_BATCH_SIZE, le=MAX_BATCH_SIZE)
    context_length: int = Field(default=2048, ge=MIN_CONTEXT_LENGTH, le=MAX_CONTEXT_LENGTH)
    temperature: float = Field(default=0.7, ge=MIN_TEMPERATURE, le=MAX_TEMPERATURE)
    max_tokens: int = Field(default=512, ge=1, le=16384)
    quantization_variant: str = Field(default="Q4_K_M", description="Quantization scheme")
    environment: str = Field(default="production", description="Target environment")
    resource_limits: dict[str, Any] = Field(
        default_factory=lambda: {"max_memory_mb": 16384, "max_cpu_utilization_pct": 90.0}
    )
    api_settings: dict[str, Any] = Field(
        default_factory=lambda: {"timeout_sec": 30.0, "max_concurrent_requests": 64}
    )


class ProductionConfigManager:
    """Manages validation, versioning, and comparison of deployment configurations."""

    @staticmethod
    def compute_config_hash(config_dict: dict[str, Any]) -> str:
        """Compute deterministic SHA-256 hash signature of configuration dict."""
        sanitized = {k: v for k, v in sorted(config_dict.items()) if k not in ["created_at", "updated_at"]}
        serialized = json.dumps(sanitized, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def generate_config_version_key(cls, config_dict: dict[str, Any]) -> str:
        """Generate formatted configuration version string (e.g. cfg-a00a6808e7)."""
        h_sig = cls.compute_config_hash(config_dict)
        return f"cfg-{h_sig[:10]}"

    @classmethod
    def validate_configuration(
        cls, config_dict: dict[str, Any], check_model_exists: bool = False
    ) -> tuple[bool, list[str], dict[str, Any]]:
        """Validate configuration schema, parameter boundaries, and optional model existence.

        Returns:
            (is_valid, list_of_error_messages, validated_dict)
        """
        errors: list[str] = []
        validated_dict: dict[str, Any] = {}

        # 1. Pydantic schema validation
        try:
            cfg_obj = ProductionRuntimeConfigSchema(**config_dict)
            validated_dict = cfg_obj.model_dump()
        except Exception as err:
            errors.append(f"Schema validation failure: {str(err)}")
            return False, errors, {}

        # 2. Resource boundary validation
        limits = validated_dict.get("resource_limits", {})
        max_mem = limits.get("max_memory_mb", 16384)
        if max_mem < 256:
            errors.append("Resource limit error: max_memory_mb must be at least 256 MB.")

        # 3. Model path / file existence check
        if check_model_exists:
            model_id = validated_dict["model_id"]
            models_dir = Path("storage/models")
            gguf_matches = list(models_dir.glob(f"*{model_id}*.gguf"))
            if not gguf_matches and not (models_dir / f"{model_id}.gguf").exists():
                errors.append(f"Model file check failed: Model '{model_id}' GGUF file not found in storage/models/")

        is_valid = len(errors) == 0
        return is_valid, errors, validated_dict

    @classmethod
    def compare_configurations(
        cls, config1: dict[str, Any], config2: dict[str, Any]
    ) -> dict[str, Any]:
        """Compare two configuration dictionaries and return parameter differences.

        Returns:
            {
                "config1_hash": str,
                "config2_hash": str,
                "match": bool,
                "differences": list[dict]
            }
        """
        hash1 = cls.compute_config_hash(config1)
        hash2 = cls.compute_config_hash(config2)
        match = hash1 == hash2

        differences: list[dict[str, Any]] = []

        all_keys = set(config1.keys()) | set(config2.keys())
        for key in sorted(all_keys):
            val1 = config1.get(key)
            val2 = config2.get(key)

            if key not in config1:
                differences.append(
                    {"parameter": key, "val1": None, "val2": val2, "status": "ADDED"}
                )
            elif key not in config2:
                differences.append(
                    {"parameter": key, "val1": val1, "val2": None, "status": "REMOVED"}
                )
            elif val1 != val2:
                differences.append(
                    {"parameter": key, "val1": val1, "val2": val2, "status": "MODIFIED"}
                )

        return {
            "config1_hash": f"cfg-{hash1[:10]}",
            "config2_hash": f"cfg-{hash2[:10]}",
            "match": match,
            "differences": differences,
        }


production_config_manager = ProductionConfigManager()
