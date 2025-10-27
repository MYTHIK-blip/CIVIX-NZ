# ⬡ CIVIX Methodology and System Design ⬡

This document outlines the core principles, infrastructure design, development methodology, and operational guidelines for the CIVIX project. It serves as a central reference for any developer or agent working on the system, ensuring consistency, clarity, and adherence to established practices.

## 1. Vision & Purpose

*   **Vision:** To build a reliable and efficient Retrieval-Augmented Generation (RAG) system specialized for navigating and understanding complex compliance documents. This system will empower users to ask natural language questions and receive accurate, context-aware answers based on a large corpus of regulatory and legal texts.
*   **Purpose:** To provide a scalable and accurate solution for querying compliance documents, automating ingestion, vectorization, retrieval, and answer generation.

## 2. Ethos & Core Principles

*   **Robustness:** Production-quality code with strong emphasis on error handling, logging, and idempotency.
*   **Testability:** Every component designed with testability in mind; comprehensive `pytest` suite.
*   **Modularity:** System built in distinct, modular phases (ingestion, retrieval, generation, UI) for clarity and maintainability.
*   **CPU-First:** Designed to run on standard CPU infrastructure by default for broad accessibility. GPU support is optional.
*   **Transparency:** Clear logging, metrics, and tracing for operational visibility.
*   **Reproducibility:** Consistent environment management via `requirements.txt`.

## 3. Infrastructure Design

### 3.1 Core Components

*   **FastAPI Backend (`ingestion_service.py`):** Provides RESTful API endpoints for document ingestion (`/ingest`) and querying (`/query`).
*   **Ingestion Pipeline (`src/ingestion/processor.py`):** Handles document parsing (PDF, DOCX, TXT), text chunking, embedding generation (`sentence-transformers`), and upserting into ChromaDB.
*   **Retrieval Pipeline (`src/retrieval/retriever.py`):** Embeds queries, performs initial ChromaDB retrieval, and applies re-ranking (`CrossEncoder`) for enhanced relevance.
*   **Generation Pipeline (`src/generation/generator.py`):** Interacts with a local Ollama server (default `mistral`) to generate answers based on retrieved context.
*   **Vector Store:** Persistent ChromaDB instance (`./data/chroma`) for storing document chunks and embeddings.
*   **Embedding Cache:** File-based cache (`./data/embed_cache`) for embeddings to ensure idempotency and speed up re-ingestion.
*   **Ingestion Manifest:** JSON file (`./data/ingestion_manifest.json`) to track processed documents.

### 3.2 User Interface (`ui.py`)

*   **Streamlit Application:** A simple, Python-native web interface for user interaction with the RAG system.

### 3.3 Observability

*   **Structured Logging:** Centralized JSON logging (`src/utils/logging_config.py`) for all components.
*   **Metrics:** Prometheus metrics (`src/utils/metrics.py`) for API endpoints and internal RAG operations. Exposed via `/metrics` endpoint.
*   **Tracing:** OpenTelemetry distributed tracing (`src/utils/tracing.py`) for visualizing request flow and latency.

## 4. Development Methodology & Cadence

*   **Phased Development:** Project progresses through distinct, well-defined phases (e.g., Phase 3: Ingestion, Phase 6: UI, Phase 8: Metrics/Tracing).
*   **Iterative Approach:** Each phase involves planning, implementation, testing, and documentation.
*   **Test-Driven Principles:** Comprehensive `pytest` suite ensures reliability and prevents regressions.
*   **CPU-First Development:** Prioritize CPU-compatible solutions by default, with optional GPU support.
*   **Documentation-Driven:** Key decisions, progress, and implementation details are logged in `docs/` and summarized in `README.md`.
*   **Continuous Documentation:** All logs, documentation (including `README.md` and this `civix_method.md` file), and code comments are updated in correspondence to any progress, issues, or resolutions encountered. This includes:
    *   **Timestamping:** All log entries and significant documentation updates are timestamped for clear historical tracking.
    *   **Formatting Cadence:** Consistent Markdown formatting is maintained across all documentation.
    *   **GitHub Cadence:** Documentation updates are committed and pushed regularly, aligning with code changes, ensuring compatibility with GitHub's rendering (e.g., fencing for code blocks, Mermaid diagrams where applicable).

## 5. GitHub and Versioning

*   **Repository:** Hosted on GitHub (`MYTHIK-blip/CIVIX-NZ`).
*   **Branching Strategy:** `main` branch for stable, production-ready code. Feature branches for new development.
*   **Commit Messages:** Follow conventional commits (e.g., `feat:`, `fix:`, `docs:`) with clear, concise descriptions. Emoticons may be used for visual categorization (e.g., ✨ for new features).
*   **Tagging:** Use lightweight tags (e.g., `v0.1.0-phase8-complete`) to mark significant milestones or release points for easy rollback and version tracking.
*   **`.gitignore`:** Carefully configured to exclude generated files, environment specifics, and sensitive data.

## 6. Constraints & Guardrails

*   **Minimal & Reversible Changes:** Prioritize small, atomic commits.
*   **No New Heavy Dependencies:** Avoid introducing unnecessary large libraries.
*   **Preserve Behavior:** Maintain functional parity; prefer `sentence-transformers` or well-documented stubs over heavy dependencies.
*   **Security First:** Never expose secrets or sensitive information.
*   **User Control:** Confirm significant actions or ambiguous requests with the user.

---
