# ArmServe Maintenance & Automation Scripts

This directory contains executable scripts for running benchmarks, executing autonomous optimization sweeps, running test suites, and validating system integrity.

## Available Scripts

- `validate_system.py`: End-to-end sanity check script for ArmServe backend, database, and inference engine.
- `run_benchmark.py`: Command-line interface to trigger isolated inference benchmark runs.

## Usage

```bash
# Run system validation
python scripts/validate_system.py

# Run standalone benchmark
python scripts/run_benchmark.py --threads 8 --batch-size 128 --model qwen2.5-0.5b-instruct
```
