# ADR 0003: TimescaleDB for Time-Series Performance Metrics

## Status
Accepted

## Context
Real-time Arm64 benchmarks and deployed inference monitors emit high-volume time-series data (percentile latencies, CPU/NEON utilization, RAM RSS, throughput). The system requires efficient analytical queries and downsampling over historical trials.

## Decision
We adopt **TimescaleDB** (PostgreSQL extension) for storing and querying time-series performance metrics.

## Rationale
1. **Unified Relational Stack**: Extends standard PostgreSQL, eliminating the need to maintain an entirely separate NoSQL/time-series database stack (e.g., InfluxDB).
2. **Hypertables & Automatic Chunking**: Automatically partitions time-series data by time interval and space for fast writes and queries.
3. **Continuous Aggregates & Compression**: High-ratio columnar compression reduces disk footprint for historical benchmark runs.
4. **Full SQL Support**: Allows complex JOIN queries between standard application metadata (experiments, models) and time-series benchmark metrics.

## Consequences
- Requires PostgreSQL database instances to load the TimescaleDB extension plugin.
- Time-series metric schemas must be partitioned as Hypertables during database migrations.
