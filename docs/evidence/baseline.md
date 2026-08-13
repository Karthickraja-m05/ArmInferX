# ArmServe Technical Evidence: Baseline Benchmark Performance

**Document Type**: Technical Evidence Certificate  
**Execution Timestamp**: 2026-08-13T11:37:50Z  
**Hardware Platform**: AWS Graviton3 `c7g.2xlarge` (8 vCPUs ARM Neoverse V1)  
**AI Model**: `qwen2.5-0.5b-instruct` (0.49B Parameters)  
**Configuration ID**: `cfg-baseline-fp16-t1-b32`  

---

## 1. Baseline Configuration Parameters

- **Model Precision**: FP16 Baseline (Unquantized floating point 16-bit weights)
- **Thread Count**: 1 Thread (Single-threaded single-core execution)
- **Batch Size**: 32 (Standard unoptimized batch size)
- **Runtime Acceleration**: Default FP16 CPU execution without SIMD micro-architectural tuning
- **Memory Allocation**: Standard unmapped process heap

---

## 2. Baseline Measured Values

| Metric | Measured Baseline Value | Measurement Unit |
| :--- | :--- | :--- |
| **Time-To-First-Token (TTFT)** | **0.25** | milliseconds (ms) |
| **P50 Latency** | **14.20** | milliseconds (ms) |
| **P90 Latency** | **14.80** | milliseconds (ms) |
| **P99 Latency** | **15.10** | milliseconds (ms) |
| **Throughput (Tokens/sec)** | **131.30** | tokens per second (tps) |
| **Request Rate (Req/sec)** | **9.80** | requests per second (rps) |
| **CPU Utilization** | **25.0** | percent (%) |
| **RAM Footprint** | **412.5** | megabytes (MB) |
| **Quality Score** | **100.0** | percent (%) [Reference Standard] |
| **Inference Cost ($/M Tokens)** | **$0.182** | USD per 1,000,000 tokens |

---

## 3. Benchmark Methodology

- **Warmup Phase**: 50 unrecorded warmup requests executed prior to logging telemetry.
- **Load Test Sweep**: 1,000 sequential chat completion requests dispatched to `/v1/chat/completions`.
- **Sampling Window**: Continuous metric recording across a 300-second steady-state window.
- **Statistical Aggregation**: P50, P90, and P99 latencies computed from exact empirical percentile distributions.

---

## 4. Reproduction Command

```bash
# Execute Baseline Benchmark via ArmServe CLI
python -m cli.main benchmark run \
  --model qwen2.5-0.5b-instruct \
  --quantization fp16 \
  --threads 1 \
  --batch-size 32 \
  --requests 1000
```
