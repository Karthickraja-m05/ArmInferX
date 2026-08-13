# ArmServe Benchmark Suite

ArmServe includes an automated benchmarking engine tailored for ARM64 Graviton infrastructure.

## Benchmark Configurations

- `default-sweep.json`: Standard 12-trial Optuna hyperparameter exploration grid.
- `performix-manifest.json`: Configuration mapping ArmServe telemetry to Arm Performix benchmark specifications.

## Running Benchmarks via CLI

```bash
# Run benchmark with custom threads and batch size
armserve benchmark run --model qwen2.5-0.5b-instruct --threads 8 --batch-size 128
```
