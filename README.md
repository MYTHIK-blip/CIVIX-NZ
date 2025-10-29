# ComplianceRAG

## Vision

To build a reliable and efficient Retrieval-Augmented Generation (RAG) system specialized for navigating and understanding complex compliance documents. This system will empower users to ask natural language questions and receive accurate, context-aware answers based on a large corpus of regulatory and legal texts.

## Ethos

*   **Robustness:** Code should be production-quality, with a strong emphasis on error handling, logging, and idempotency.
*   **Testability:** Every component should be designed with testability in mind. A comprehensive test suite is non-negotiable.
*   **Modularity:** The system is built in distinct, modular phases (ingestion, retrieval, generation) to ensure clarity and maintainability.
*   **CPU-First:** The system is designed to run on standard CPU infrastructure by default, ensuring broad accessibility. GPU support can be enabled but is not a requirement.

## Purpose

The primary purpose of ComplianceRAG is to provide a scalable and accurate solution for querying compliance documents. It automates the process of ingesting and vectorizing a large volume of text data, and provides an interface for users to retrieve relevant information and generate coherent answers.

## Current Standing (as of 2025-10-28)

**Phase 3: Ingestion Pipeline - COMPLETE**
**Phase 4: Retrieval Endpoint - COMPLETE**
**Phase 5: Generation Pipeline - COMPLETE**
**Phase 6: User Interface (Streamlit) - COMPLETE**
**Phase 7: Monitoring & Observability (Structured Logging) - COMPLETE**
**Phase 8: Monitoring & Observability (Metrics & Tracing) - COMPLETE**
**Phase 9: User Interface Enhancements - COMPLETE**
**Phase 10: System Evaluation and Benchmarking - COMPLETE**

All critical issues identified during Phase 10, including embedding model loading, cache invalidation, and test assertion logic, have been successfully resolved. The project's test suite now passes consistently.

The project currently has a fully functional and robust document ingestion pipeline, a retrieval endpoint, and a generation pipeline, all integrated with a user-friendly Streamlit interface and comprehensive observability features. Key features include:

*   **API:** A FastAPI service (`ingestion_service.py`) with an `/ingest` endpoint for document uploads and a `/query` endpoint for retrieving relevant document chunks and generating answers.
*   **Document Processing:** Support for PDF, DOCX, and TXT file formats.
*   **Vectorization:** A sophisticated pipeline (`src/ingestion/processor.py`) that chunks text, generates embeddings using `sentence-transformers`, and upserts them into a ChromaDB vector store, storing the document text itself.
*   **Advanced Retrieval:** A dedicated module (`src/retrieval/retriever.py`) that embeds user queries, performs initial retrieval, and applies re-ranking for enhanced relevance.
*   **Legal Entity Recognition (NER):** Extracts key legal entities (e.g., organizations, regulations, dates) from ingested documents, stored as metadata for enhanced search and analysis.
*   **Generation:** A dedicated module (`src/generation/generator.py`) that interacts with a local Ollama server (e.g., `mistral`) to construct RAG-specific prompts and generate answers based on retrieved context.
*   **User Interface:** A Streamlit application (`ui.py`) providing document upload, query history, configurable retrieval parameters, and enhanced display of retrieved content.
*   **Observability:** Structured JSON logging, Prometheus metrics, and OpenTelemetry distributed tracing for comprehensive system monitoring.
*   **Benchmarking:** A script (`scripts/benchmark.py`) for automated end-to-end system evaluation.
*   **Idempotency & Caching:** The ingestion pipeline is idempotent. It uses a file-based cache for embeddings and a manifest file to track ingested documents, preventing redundant processing.
*   **Persistence:** The system uses a persistent, on-disk ChromaDB instance for the main application.
*   **Testing:** A comprehensive `pytest` suite is in place, ensuring the reliability of the ingestion, retrieval, and generation processes.

## Versioning and Release Management

The project follows a clear versioning strategy, utilizing release branches and tags for stability and traceability.

## Versioning and Release Management

The project employs a robust versioning and release management strategy to ensure stability, traceability, and ease of rollback.

*   **Release Branches:** For significant milestones or production-ready states, a dedicated `release-YYYY-MM-DD` branch is created from `main`. These branches serve as frozen points for stability.
*   **Tagging:** Lightweight tags (e.g., `v0.1.0-release-YYYY-MM-DD`) are applied to release branches to mark specific versions, facilitating easy identification and rollback.
*   **Git LFS:** Large files, such as model checkpoints (`.safetensors`), are managed using Git Large File Storage (LFS) to maintain repository performance and integrity.

## Notes for Future Developers (Human or AI)

For detailed instructions on setting up, running, and testing the system, please refer to the [How to Run the CIVIX System Guide](docs/how-to/run_system.md).

1.  **Development Environment:** Always use the virtual environment (`source venv/bin/activate`). All dependencies are listed in `requirements.txt`.

2.  **CPU-First Installation (Torch):** This project is configured for CPU-first operation. To install PyTorch for CPU, use the following command:
    ```bash
    pip install torch --index-url https://download.pytorch.org/whl/cpu
    ```
    If you require GPU support, you will need to install the appropriate CUDA-enabled PyTorch wheel separately, following the instructions on the official PyTorch website (e.g., `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118` for CUDA 11.8).

3.  **Embedding Model for Testing:** For consistent test execution, the `all-MiniLM-L6-v2` embedding model is expected to be available locally. If not present, it can be downloaded and saved to `./models/all-MiniLM-L6-v2`. When running tests, ensure the `EMBED_MODEL` environment variable is set to this local path (e.g., `EMBED_MODEL=./models/all-MiniLM-L6-v2 pytest`).

4.  **Testing with ChromaDB:** During development, a critical issue was discovered with `chromadb.PersistentClient` causing database locks during rapid test execution. **The test suite now uses `chromadb.PersistentClient` with unique temporary directories for each test or module to ensure true isolation.** This was a complex issue to resolve, highlighting the importance of proper test isolation for stateful components. The production code correctly uses the `PersistentClient`.

5.  **Idempotency:** The ingestion pipeline is designed to be idempotent. Re-ingesting the same file will not create duplicate entries or re-compute embeddings that are already in the cache. This is a core feature; please maintain it.

6.  **Configuration:** Key parameters (model name, device, paths) are controlled via environment variables with sensible defaults in `src/ingestion/processor.py`, `src/retrieval/retriever.py`, and `src/generation/generator.py`. For production deployments, consider using a more formal configuration management system (e.g., a `.env` file loader or a settings module).

7.  **Ollama Server:** For the generation pipeline to function, an Ollama server must be running locally (or at the configured `OLLAMA_API_BASE_URL`) with the specified model (`OLLAMA_MODEL`, e.g., `mistral`) pulled and ready. You can start it with `ollama run mistral`.

8.  **Post-Phase 10 Debugging Notes:**
    *   **Ollama Model Alias:** The system expects a model named `mistral`. If only `mistral:instruct` is available, create an alias using `ollama cp mistral:instruct mistral`.
    *   **Character-Based Chunking:** Due to the removal of `transformers` for CPU-first optimization, the system defaults to character-based chunking. Ensure `CHUNK_SIZE_CHARS` and `CHUNK_OVERLAP_CHARS` in `src/ingestion/processor.py` are appropriately configured for your document sizes to achieve optimal chunking. Initial debugging revealed that default values were too large for smaller documents, leading to single-chunk ingestion.


## Phase 6: User Interface (Streamlit) - Enhanced

The Streamlit UI has been enhanced with additional features for improved user interaction.

### Features:
*   **Document Upload:** Upload PDF, DOCX, or TXT files directly via the UI for ingestion into the RAG system.
*   **Query History:** View a session-based history of past queries, generated answers, and retrieved contextual chunks.
*   **Configurable Retrieval:** Adjust `top_k` (initial chunks for retrieval) and `rerank_k` (final chunks after re-ranking) using sliders.
*   **Enhanced Context Display:** Retrieved chunks are displayed with their content and metadata for transparency.

### To run the user interface:

1.  **Ensure FastAPI Backend is Running:** The Streamlit UI communicates with the FastAPI backend. Make sure your `ingestion_service.py` is running. You can start it with:
    ```bash
    source .venv/bin/activate
    uvicorn ingestion_service:app --reload
    ```
    (Note: You might need to adjust the host/port if not running on default `http://localhost:8000`).

2.  **Install Streamlit:** If you haven't already, install Streamlit (it's included in `requirements.txt`):
    ```bash
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Run the Streamlit App:**
    ```bash
    source .venv/bin/activate
    streamlit run ui.py
    ```
    This will open the UI in your web browser, typically at `http://localhost:8501`.

## Phase 7: Monitoring & Observability (Metrics & Tracing)

The FastAPI backend is instrumented with Prometheus metrics and OpenTelemetry tracing.

### Running with Metrics and Tracing

1.  **Ensure Dependencies are Installed:**
    ```bash
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Start a Tracing Collector (e.g., Jaeger):**
    For local development, you can run Jaeger with Docker:
    ```bash
    docker run -d --name jaeger \
      -e COLLECTOR_OTLP_ENABLED=true \
      -p 16686:16686 \
      -p 4317:4317 \
      jaegertracing/all-in-one:latest
    ```
    Access Jaeger UI at `http://localhost:16686`.

3.  **Start the FastAPI Backend with Tracing Enabled:**
    Set the `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable to point to your Jaeger collector (default is `http://localhost:4317`).
    ```bash
    source .venv/bin/activate
    export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317" # Or your collector's OTLP gRPC endpoint
    uvicorn ingestion_service:app --reload
    ```

### Viewing Metrics

*   Access Prometheus metrics at `http://localhost:8000/metrics` (assuming your FastAPI app is running on port 8000).
*   You can then configure Prometheus to scrape this endpoint.

### Viewing Traces

*   After making requests to your FastAPI application (e.g., via the Streamlit UI or directly), traces will be sent to the configured OTLP endpoint.
*   View traces in your Jaeger UI (e.g., `http://localhost:16686`). Search for service name `compliance-rag-api`.

## Benchmarking

A benchmark script is available at `scripts/benchmark.py` to evaluate the end-to-end performance of the RAG pipeline.

### Features

*   **Automated Ingestion:** Ingests a test document before running queries.
*   **Query Evaluation:** Runs a set of predefined queries from `data/evaluation_dataset.json`.
*   **Metrics:** Calculates and displays the following metrics:
    *   **Latency:** The time taken to get a response from the query endpoint.
    *   **Answer Match:** Whether the generated answer contains the "gold" answer.
    *   **Retrieval Success:** Whether the retrieved document chunks are relevant.

### How to Run

1.  **Ensure the FastAPI backend is running:**
    ```bash
    source .venv/bin/activate
    uvicorn ingestion_service:app --reload
    ```

2.  **Run the benchmark script:**
    ```bash
    source .venv/bin/activate
    python scripts/benchmark.py
    ```
