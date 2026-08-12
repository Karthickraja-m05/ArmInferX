# ADR 0004: Celery and Redis for Asynchronous Task Processing

## Status
Accepted

## Context
Optimization runs, infrastructure provisioning, real benchmark executions, model downloads, and deployments are long-running operations ranging from minutes to hours. They must be decoupled from the synchronous HTTP request-response cycle.

## Decision
We select **Celery** as the distributed task queue framework with **Redis 7** as the message broker and cache layer.

## Rationale
1. **Task Scheduling & Retries**: Offers robust task routing, rate limiting, retry mechanisms, and state tracking.
2. **Horizontal Scalability**: Worker instances can scale dynamically on Kubernetes node pools.
3. **Redis Versatility**: Serves as high-speed Celery broker, application caching layer, and WebSocket pub/sub fan-out broker simultaneously.

## Consequences
- Requires idempotent task design so that retried operations do not create orphan compute resources.
- Celery worker memory usage must be monitored to handle heavy model manipulation scripts.
