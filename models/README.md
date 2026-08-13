# ArmServe Supported AI Models

ArmServe optimizes GGUF quantized and ONNX Runtime accelerated LLM models on ARM64 Graviton architecture.

## Default Model Specification

- **Model ID**: `qwen2.5-0.5b-instruct`
- **Architecture**: Qwen2.5 (0.49B Parameters)
- **Quantization**: `GGUF (Q4_K_M)` / ONNX Runtime MLAS
- **Vector Acceleration**: ARM Neoverse V1 SIMD (`bf16` + `i8mm`)
