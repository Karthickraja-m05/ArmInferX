"""Model registry schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ModelRegister(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    source: str = Field(description="e.g., huggingface:meta-llama/Meta-Llama-3-8B")
    format: str = Field(default="ONNX", description="PYTORCH, ONNX, GGUF, SAFETENSORS")
    quantization: str = Field(default="NONE", description="FP32, FP16, INT8, INT4, NONE")


class ModelResponse(BaseModel):
    id: UUID
    name: str
    source: str
    format: str
    quantization: str
    size_bytes: int | None = None
    storage_uri: str | None = None
    checksum_sha256: str | None = None
    compatible_runtimes: list[str] = Field(default_factory=list)
    metadata_info: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
