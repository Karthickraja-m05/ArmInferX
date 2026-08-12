# ArmServe Runtime Configuration Specification

This document details the strongly-typed runtime configuration schema, environment variable overrides, validation boundaries, and startup verification rules for the ArmServe AI Inference Runtime.

---

## 1. Runtime Configuration Schema

Runtime behavior is governed by the `RuntimeConfig` class defined in [`backend/app/core/config.py`](file:///c:/Users/mm989/Downloads/Study/ArmInferX/backend/app/core/config.py). All options support environment variable overrides prefixed with `ARMSERVE_RUNTIME__`.

```text
ARMSERVE_RUNTIME__MODEL_PATH="storage/models/qwen2.5-0.5b-instruct-q4_k_m.gguf"
ARMSERVE_RUNTIME__CONTEXT_LENGTH=2048
ARMSERVE_RUNTIME__THREAD_COUNT=4
ARMSERVE_RUNTIME__TEMPERATURE=0.7
ARMSERVE_RUNTIME__MAX_TOKENS=256
ARMSERVE_RUNTIME__BATCH_SIZE=128
ARMSERVE_RUNTIME__SERVER_PORT=8000
ARMSERVE_RUNTIME__TIMEOUT_SECONDS=60.0
```

---

## 2. Configuration Options & Boundaries Matrix

| Configuration Option | Environment Variable | Data Type | Default Value | Valid Range / Constraints | Description |
|---|---|---|---|---|---|
| **`model_path`** | `ARMSERVE_RUNTIME__MODEL_PATH` | `str` | `"storage/models/..."` | Valid file path | Target GGUF / ONNX model file location |
| **`context_length`** | `ARMSERVE_RUNTIME__CONTEXT_LENGTH` | `int` | `2048` | `128` to `32768` | Maximum token context window size |
| **`thread_count`** | `ARMSERVE_RUNTIME__THREAD_COUNT` | `int` | `4` | `1` to `128` | Number of CPU execution threads allocated |
| **`temperature`** | `ARMSERVE_RUNTIME__TEMPERATURE` | `float` | `0.7` | `0.0` to `2.0` | Sampling temperature for text generation |
| **`max_tokens`** | `ARMSERVE_RUNTIME__MAX_TOKENS` | `int` | `256` | `1` to `4096` | Maximum generation completion tokens |
| **`batch_size`** | `ARMSERVE_RUNTIME__BATCH_SIZE` | `int` | `128` | `1` to `2048` | Prompt token evaluation batch size |
| **`server_port`** | `ARMSERVE_RUNTIME__SERVER_PORT` | `int` | `8000` | `1024` to `65535` | Listening port for FastAPI REST API |
| **`timeout_seconds`** | `ARMSERVE_RUNTIME__TIMEOUT_SECONDS` | `float` | `60.0` | `1.0` to `600.0` | Request timeout limit in seconds |

---

## 3. Startup Validation & Exception Handling

- **Pydantic Validation**: At application boot, `ArmServeSettings` parses environment variables and validates types and ranges.
- **Fail-Fast Policy**: If an invalid value is supplied (e.g. `thread_count=0` or `temperature=3.5`), Pydantic raises a `ValidationError` and halts startup immediately to prevent undefined C++ runtime crashes.
- **Dynamic Configuration Injection**: `InferenceEngine` reads parameters directly from `settings.runtime`, guaranteeing zero hardcoded runtime constants.
