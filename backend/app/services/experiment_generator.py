"""ArmServe Optimization Experiment Configuration Generator.

Generates validated parameter combinations for optimization experiments using grid search,
fixed values, and constraint rules to eliminate invalid or duplicate runtime configurations.
"""

import hashlib
import itertools
import json
from pathlib import Path
import platform
import time
from typing import Any

import psutil
import structlog
from pydantic import BaseModel, ConfigDict, Field

logger = structlog.get_logger("backend.app.services.experiment_generator")

CONFIGS_DIR = Path("storage/experiments/configs")


class ExperimentConfigRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    config_id: str
    created_at: str
    model_id: str = "qwen2.5-0.5b-instruct"
    thread_count: int = 4
    batch_size: int = 128
    context_length: int = 2048
    temperature: float = 0.7
    max_tokens: int = 256
    gpu_layers: int = 0
    quantization_variant: str = "Q4_K_M"
    hash_signature: str


class ParameterRangeSpec(BaseModel):
    thread_counts: list[int] = Field(default_factory=lambda: [1, 2, 4, 8])
    batch_sizes: list[int] = Field(default_factory=lambda: [32, 64, 128, 256])
    context_lengths: list[int] = Field(default_factory=lambda: [2048])
    temperatures: list[float] = Field(default_factory=lambda: [0.0, 0.7])
    max_tokens_list: list[int] = Field(default_factory=lambda: [256])
    model_id: str = "qwen2.5-0.5b-instruct"


class ConfigurationGenerator:
    """Production Experiment Configuration Matrix Generator."""

    def __init__(self) -> None:
        CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
        self.max_vcpus = psutil.cpu_count(logical=True) or 16

    def compute_config_hash(self, params: dict[str, Any]) -> str:
        """Compute unique deterministic SHA-256 hash for parameter set."""
        canonical_str = json.dumps(params, sort_keys=True)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()[:16]

    def validate_parameter_constraints(self, params: dict[str, Any]) -> bool:
        """Validate logical hardware and software constraints."""
        threads = params.get("thread_count", 4)
        batch = params.get("batch_size", 128)
        context = params.get("context_length", 2048)
        temp = params.get("temperature", 0.7)

        # Constraint 1: Thread count must not exceed system vCPUs * 2
        if threads < 1 or threads > self.max_vcpus * 2:
            return False

        # Constraint 2: Batch size must not exceed context length
        if batch < 1 or batch > context:
            return False

        # Constraint 3: Temperature must be between 0.0 and 2.0
        if temp < 0.0 or temp > 2.0:
            return False

        return True

    def generate_configurations(self, spec: ParameterRangeSpec) -> list[ExperimentConfigRecord]:
        """Generate deduplicated, validated experiment configurations."""
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        generated_configs: list[ExperimentConfigRecord] = []
        seen_hashes: set[str] = set()

        # Load existing hashes to prevent duplicates
        for existing_file in CONFIGS_DIR.glob("*.json"):
            try:
                with open(existing_file, encoding="utf-8") as f:
                    data = json.load(f)
                    if "hash_signature" in data:
                        seen_hashes.add(data["hash_signature"])
            except Exception:
                pass

        # Cartesian product of parameter options
        combinations = itertools.product(
            spec.thread_counts,
            spec.batch_sizes,
            spec.context_lengths,
            spec.temperatures,
            spec.max_tokens_list,
        )

        for t_count, b_size, c_len, temp, m_tok in combinations:
            params = {
                "model_id": spec.model_id,
                "thread_count": t_count,
                "batch_size": b_size,
                "context_length": c_len,
                "temperature": temp,
                "max_tokens": m_tok,
                "gpu_layers": 0,
                "quantization_variant": "Q4_K_M",
            }

            # 1. Check constraints
            if not self.validate_parameter_constraints(params):
                continue

            # 2. Check deduplication
            sig = self.compute_config_hash(params)
            if sig in seen_hashes:
                continue

            seen_hashes.add(sig)
            config_id = f"cfg-{sig[:10]}"

            cfg_record = ExperimentConfigRecord(
                config_id=config_id,
                created_at=now_str,
                model_id=spec.model_id,
                thread_count=t_count,
                batch_size=b_size,
                context_length=c_len,
                temperature=temp,
                max_tokens=m_tok,
                gpu_layers=0,
                quantization_variant="Q4_K_M",
                hash_signature=sig,
            )

            # 3. Store configuration manifest
            out_file = CONFIGS_DIR / f"{config_id}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(cfg_record.model_dump_json(indent=2))

            generated_configs.append(cfg_record)

        logger.info("Generated valid experiment configurations", count=len(generated_configs))
        return generated_configs
