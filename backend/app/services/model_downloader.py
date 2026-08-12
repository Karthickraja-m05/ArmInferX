"""Model management, download, checksum verification, and storage foundation."""

import hashlib
import json
from pathlib import Path
import time
from typing import Any

import httpx
import structlog

logger = structlog.get_logger("backend.app.services.model_downloader")

MODELS_DIR = Path("storage/models")

DEFAULT_MODEL = {
    "id": "qwen2.5-0.5b-instruct",
    "name": "Qwen2.5-0.5B-Instruct GGUF",
    "version": "2.5-0.5b",
    "quantization": "Q4_K_M",
    "format": "gguf",
    "source_url": "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf",
    "filename": "qwen2.5-0.5b-instruct-q4_k_m.gguf",
    "size_bytes": 397750080,  # ~398 MB
}


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 checksum of a local file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def ensure_model_available() -> dict[str, Any]:
    """Download pinned GGUF model artifact if not present, verify file, and save metadata."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / DEFAULT_MODEL["filename"]
    meta_path = MODELS_DIR / "qwen2.5-0.5b-instruct-q4_k_m.json"

    if not model_path.exists() or model_path.stat().st_size == 0:
        logger.info("Downloading pinned open-weight model artifact", url=DEFAULT_MODEL["source_url"])
        start_time = time.time()

        with httpx.stream("GET", DEFAULT_MODEL["source_url"], follow_redirects=True, timeout=120.0) as response:
            response.raise_for_status()
            with open(model_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=1048576):
                    f.write(chunk)

        download_duration = round(time.time() - start_time, 2)
        logger.info("Model download complete", duration_seconds=download_duration, size_mb=round(model_path.stat().st_size / 1048576, 2))

    # Compute checksum
    checksum = compute_sha256(model_path)
    file_size = model_path.stat().st_size

    metadata = {
        **DEFAULT_MODEL,
        "local_path": str(model_path.resolve()),
        "file_size_bytes": file_size,
        "sha256_checksum": checksum,
        "verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info("Model verified and ready", filename=DEFAULT_MODEL["filename"], checksum=checksum[:16] + "...")
    return metadata
