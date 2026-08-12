# ArmServe Production Performance Benchmark Methodology Specification

**Role**: Performance Benchmark Architect  
**Target Architecture**: AWS Graviton3 (ARM64 Neoverse V1)  
**Execution Objective**: Standardized, reproducible benchmarking for CPU-only LLM inference latencies and throughputs.

---

## 1. Core Benchmark Telemetry & Metrics Definition

| Telemetry Metric | Symbol / Unit | Calculation / Measurement Method | Target SLA / KPI |
|---|---|---|---|
| **Time To First Token (TTFT)** | $T_{\text{TTFT}}$ (ms) | Time elapsed from initial request dispatch until first SSE token chunk is emitted. | $< 15\text{ ms}$ |
| **Total Response Latency** | $T_{\text{total}}$ (ms) | Total end-to-end HTTP request duration from TCP connect to connection close. | $< 100\text{ ms}$ |
| **Tokens Per Second (TPS)** | $\text{TPS}$ (tok/s) | $\frac{N_{\text{completion\_tokens}}}{T_{\text{generation\_duration}}}$ | $> 50\text{ tok/s}$ |
| **Prompt Processing Time** | $T_{\text{prompt}}$ (ms) | Time spent in prefill stage processing prompt tokens. | $< 10\text{ ms}$ |
| **Generation Time** | $T_{\text{gen}}$ (ms) | Time spent in autoregressive token decoding loop. | $< 50\text{ ms}$ |
| **Requests Per Second (RPS)** | $\text{RPS}$ (req/s) | Total completed HTTP requests divided by test duration. | $> 100\text{ req/s}$ |
| **Concurrent Performance** | $P_{\text{conc}}$ | Latency distribution (P50, P90, P99) under concurrent load (1, 2, 4, 8, 16 workers). | P99 $< 200\text{ ms}$ |
| **Peak Memory Usage** | $M_{\text{peak}}$ (MB) | Maximum resident set size (RSS) during trial run. | $< 2,048\text{ MB}$ |
| **Average Memory Usage** | $M_{\text{avg}}$ (MB) | Mean resident set size across test iteration window. | $< 1,024\text{ MB}$ |
| **CPU Utilization** | $C_{\text{cpu}}$ (%) | Percentage of vCPU capacity active across 4 vCPUs. | $< 80\%$ |
| **Error Rate** | $E_{\text{rate}}$ (%) | $\frac{N_{\text{failed\_requests}}}{N_{\text{total\_requests}}} \times 100$ | $0.00\%$ |

---

## 2. Standardized Workload Execution Protocol

### A. Warmup Strategy
- Prior to recording benchmark metrics, **5 warmup iterations** are executed.
- Warmup requests pre-allocate C++ thread pools, initialize memory-mapped GGUF weights, and eliminate cold-start cache misses.

### B. Fixed Workload Prompt Suite
Deterministic evaluation uses three fixed prompt sizes:
1. **Short Prompt (20 tokens)**: *"Hello ArmServe! Explain ARM64 Neoverse V1 SIMD vectorization."*
2. **Medium Prompt (100 tokens)**: *"Compare ARM64 CPU-only inference against x86 architecture for open-weight language models."*
3. **Long Prompt (500 tokens)**: *"Provide a detailed technical breakdown of ONNX Runtime MLAS matrix multiplication kernels on AWS Graviton3."*

### C. Deterministic Generation Settings
To ensure 100% reproducible results across trial runs:
- `temperature`: `0.0` (greedy decoding)
- `top_p`: `1.0`
- `seed`: `42`
- `max_tokens`: `128`

### D. Concurrency Scaling Matrix
Trial benchmarks execute across 5 concurrency levels: `1`, `2`, `4`, `8`, and `16` concurrent worker threads.

---

## 3. Metadata & Environment Capture Specification

Every benchmark run exports a immutable JSON result manifest containing:
```json
{
  "benchmark_run_id": "bench-20260812-a1b2c3d4",
  "timestamp": "2026-08-12T22:15:00Z",
  "environment": {
    "hostname": "armserve-graviton-01",
    "architecture": "aarch64",
    "cpu_model": "AWS Graviton3 (Neoverse V1)",
    "vcpu_count": 4,
    "ram_total_mb": 8192,
    "os": "Ubuntu 22.04.4 LTS",
    "kernel": "Linux 6.2.0-1018-aws"
  },
  "runtime_config": {
    "engine": "ArmServe-GGUF-MLAS",
    "model_id": "qwen2.5-0.5b-instruct",
    "quantization": "Q4_K_M",
    "thread_count": 4,
    "context_length": 2048
  },
  "workload_params": {
    "warmup_iterations": 5,
    "test_iterations": 20,
    "concurrency_level": 4
  },
  "results": {
    "total_requests": 20,
    "successful_requests": 20,
    "failed_requests": 0,
    "throughput_rps": 118.5,
    "tokens_per_sec": 54.2,
    "latency_p50_ms": 7.42,
    "latency_p90_ms": 9.15,
    "latency_p99_ms": 11.30,
    "peak_memory_mb": 512.4
  }
}
```
