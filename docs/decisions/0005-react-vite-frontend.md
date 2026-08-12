# ADR 0005: React and Vite for Web Frontend

## Status
Accepted

## Context
ArmServe users require a responsive, modern web console to visualize real-time benchmark execution, inspect latency histograms, manage model registries, and trigger infrastructure deployments.

## Decision
We select **React 18** with **Vite** and **TypeScript** for building the web dashboard SPA.

## Rationale
1. **Sub-second Build & Dev Experience**: Vite provides lightning-fast HMR and optimized production bundles.
2. **Rich Data Visualization Ecosystem**: Compatible with established charting libraries (`Recharts`, `Nivo`) for rendering benchmark metrics.
3. **Type Safety**: Shared data structures between Backend Pydantic models and Frontend TypeScript interfaces via generated OpenAPI types.

## Consequences
- Requires continuous maintenance of TypeScript client models matching API endpoints.
- SPA static files are served via Nginx in Docker or AWS CloudFront in production.
