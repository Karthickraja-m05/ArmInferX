# ADR 0002: Optuna for Optimization Agent Engine

## Status
Accepted

## Context
ArmServe must explore non-linear multi-objective optimization search spaces (runtime parameters, CPU thread allocations, quantization formats, batch sizes) to find Pareto-optimal configurations balancing latency, throughput, quality, and cost.

## Decision
We select **Optuna** as the core optimization library inside the Optimization Agent component.

## Rationale
1. **Flexible Search Space Definition**: Proposes hyperparameter values dynamically using pythonic conditional logic.
2. **State-of-the-Art Samplers**: Provides Tree-structured Parzen Estimators (TPE) and NSGA-II algorithms for multi-objective optimization.
3. **Pruning Capabilities**: Early stopping of sub-optimal trials to minimize benchmark compute costs.
4. **Stateless Operations**: Supports decoupled persistent storage drivers, fitting Celery asynchronous worker environments.

## Consequences
- Multi-objective targets (e.g., minimize latency AND maximize throughput) must be formally mapped to Optuna objectives.
- Trial evaluation callbacks must handle real benchmark execution failures gracefully.
