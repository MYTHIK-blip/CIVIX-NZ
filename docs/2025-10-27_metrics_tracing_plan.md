# Project Log: ComplianceRAG

**Date:** 2025-10-27

## Subject: Phase 8: Monitoring & Observability (Metrics & Tracing) - Planning

### Summary

This document outlines the plan for Phase 8, focusing on enhancing the system's monitoring and observability capabilities through the implementation of metrics collection and distributed tracing. This phase aims to provide deeper insights into the system's performance, latency, and component interactions, building upon the structured logging established in Phase 7.

### Goal

Implement basic metrics collection and distributed tracing to gain deeper insights into the system's performance, latency, and component interactions.

### Key Areas

1.  **Metrics Collection:**
    *   **API Endpoint Metrics:** Track request count, request duration, and error rates for FastAPI endpoints (`/ingest`, `/query`).
    *   **Internal Component Metrics:** Track execution times for key functions within `processor.py`, `retriever.py` (embedding, re-ranking, ChromaDB queries), and `generator.py` (Ollama API calls).
    *   **Tooling:** Use Prometheus client library for Python to expose metrics.

2.  **Distributed Tracing:**
    *   **Trace Propagation:** Propagate trace contexts across service boundaries (e.g., from FastAPI to internal components).
    *   **Span Creation:** Create spans for significant operations within each component to visualize the flow and latency of requests.
    *   **Tooling:** Use OpenTelemetry for Python to instrument the application.

### Impacted Modules

*   `ingestion_service.py` (FastAPI endpoints)
*   `src/ingestion/processor.py`
*   `src/retrieval/retriever.py`
*   `src/generation/generator.py`
*   Potentially new utility modules: `src/utils/metrics.py` and `src/utils/tracing.py` for centralized instrumentation.

### Implementation Steps

1.  **Update `requirements.txt`:** Add necessary libraries (`prometheus_client`, `opentelemetry-sdk`, `opentelemetry-api`, `opentelemetry-exporter-otlp-proto-grpc`, `opentelemetry-instrumentation-fastapi`, etc.).
2.  **Metrics Setup:**
    *   Create a new module (e.g., `src/utils/metrics.py`) to define Prometheus metrics (Counters, Histograms, Summaries).
    *   Expose a `/metrics` endpoint in `ingestion_service.py` using `prometheus_client`.
    *   Instrument key functions/operations in `ingestion_service.py`, `processor.py`, `retrieval.py`, `generator.py` with these metrics.
3.  **Tracing Setup:**
    *   Create a new module (e.g., `src/utils/tracing.py`) to configure OpenTelemetry (TracerProvider, SpanProcessor, Exporter).
    *   Instrument FastAPI with `opentelemetry-instrumentation-fastapi`.
    *   Manually create spans for critical operations within `processor.py`, `retrieval.py`, `generator.py` to trace their execution.
    *   Configure an OTLP exporter to send traces to a collector (e.g., Jaeger, Tempo).
4.  **Update `README.md`:** Add instructions on how to run with metrics/tracing enabled and how to view them (e.g., with Prometheus/Grafana/Jaeger).
5.  **Create a new log entry in `docs/`:** Document the implementation of metrics and tracing.

### Status

This document serves as the planning phase for Phase 8. Implementation will commence upon approval.
