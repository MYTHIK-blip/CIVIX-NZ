# Project Log: ComplianceRAG

**Date:** 2025-10-26

## Subject: Phase 3, 4 & 5 Implementation and Testing

### Summary

This log entry details the work completed for Phase 3 (Ingestion Pipeline), Phase 4 (Retrieval Endpoint), and Phase 5 (Generation Pipeline) of the ComplianceRAG project. All phases are now complete, tested, and verified.

### Phase 3: Ingestion Pipeline - Key Deliverables

1.  **Ingestion Processor (`src/ingestion/processor.py`):**
    *   Implemented the core `ingest_document` function.
    *   Handles parsing of PDF, DOCX, and TXT files.
    *   Features semantic text chunking with a fallback to character-based chunking.
    *   Computes unique hashes for each chunk for idempotency.
    *   Implements a file-based caching layer for embeddings to avoid re-computation.
    *   Embeds text in batches using the `all-MiniLM-L6-v2` model.
    *   Upserts chunks, metadata, and **document text** into a persistent ChromaDB collection (`compliance_chunks`).
    *   Maintains a detailed `ingestion_manifest.json` to track the status of all processed documents and chunks.

2.  **Ingestion Service (`ingestion_service.py`):**
    *   A FastAPI service was created to expose the ingestion pipeline via a `/ingest/` endpoint.
    *   The endpoint handles file uploads, saves them temporarily, and calls the ingestion processor.

3.  **Unit Tests (`tests/test_ingest_pipeline.py`):**
    *   A comprehensive test suite was developed using `pytest`.
    *   Tests cover successful ingestion, idempotency (verifying that re-ingestion uses the cache and does not create duplicates), and data cleanup.

4.  **Documentation:**
    *   `README_PHASE3.md`: A detailed runbook for setting up the environment and running the service and tests.
    *   `requirements.txt`: A file listing all project dependencies.

### Phase 4: Retrieval Endpoint - Key Deliverables

1.  **Retrieval Module (`src/retrieval/retriever.py`):**
    *   Implemented the `query_collection` function.
    *   Loads the `all-MiniLM-L6-v2` embedding model.
    *   Connects to the persistent ChromaDB at `./data/chroma`.
    *   Embeds user queries and retrieves the `top_k` most relevant document chunks from the `compliance_chunks` collection.

2.  **API Integration (`ingestion_service.py`):**
    *   Added a new `/query` FastAPI endpoint.
    *   This endpoint accepts a `query_text` and `top_k` parameter.
    *   It calls the `query_collection` function and returns the retrieved chunks as a JSON response.

3.  **Unit Tests (`tests/test_retrieval_pipeline.py`):**
    *   A new test file was created to validate the retrieval process.
    *   Tests include scenarios for relevant queries (expecting correct document chunks) and irrelevant queries (expecting high distance scores).

### Phase 5: Generation Pipeline - Key Deliverables

1.  **Generation Module (`src/generation/generator.py`):**
    *   Implemented the `generate_answer` function.
    *   Interacts with a local Ollama server (defaulting to `http://localhost:11434`) to leverage LLMs like `mistral`.
    *   Constructs a RAG-specific prompt using the user's query and retrieved context.
    *   Handles API calls to Ollama and parses the generated response.

2.  **API Integration (`ingestion_service.py`):**
    *   The existing `/query` endpoint was enhanced to integrate the generation step.
    *   It now first retrieves relevant chunks using `query_collection` and then passes these chunks, along with the user's query, to `generate_answer`.
    *   The endpoint returns the generated answer, along with the retrieved chunks for transparency.

3.  **Unit Tests (`tests/test_generation_pipeline.py`):**
    *   A new test file was created to validate the generation process.
    *   Tests mock the `httpx.post` calls to the Ollama API to ensure predictable and fast testing without requiring a running Ollama server.
    *   Includes tests for successful answer generation, handling of no retrieved chunks, and a full RAG pipeline test.

### Challenges and Resolutions

**1. ChromaDB Isolation in Tests (Phases 3, 4 & 5):**

*   **Issue:** Ensuring true isolation for ChromaDB instances across different test functions and modules proved challenging, leading to state leakage and incorrect test results (e.g., `assert 2 == 1`). Initial attempts with `EphemeralClient` and `os.environ` proved insufficient.
*   **Resolution:** The most robust solution was implemented: using `chromadb.PersistentClient` with unique temporary directories for each test or module. `pytest`'s `tmp_path` and `tmp_path_factory` fixtures were leveraged to create these isolated, temporary storage locations for ChromaDB, ensuring no state leakage between tests.

**2. Missing Document Text in Retrieval (Phase 4):**

*   **Issue:** Initial retrieval attempts returned `None` for document text, leading to `TypeError` in tests.
*   **Resolution:** The `_upsert_to_chroma` function in `src/ingestion/processor.py` was modified to explicitly store the `documents` (chunk text) in ChromaDB during ingestion. This ensures that the `query_collection` function can retrieve the actual text content.

**3. Irrelevant Query Testing Logic (Phase 4):**

*   **Issue:** The initial test for irrelevant queries incorrectly asserted that no document would be returned. Vector databases always return the closest matches, even if they are poor.
*   **Resolution:** The test `test_retrieval_no_results` was updated to assert that the `distance` score of the retrieved chunk is above a high threshold (e.g., `0.8` for cosine distance), correctly indicating a very poor match for an irrelevant query.

### Verification

All 7 tests (2 for ingestion, 2 for retrieval, 3 for generation) passed successfully. Verification steps confirmed:
*   The ChromaDB collection was correctly populated with embeddings, metadata, and document text.
*   The ingestion manifest was accurately updated.
*   The caching mechanism functioned as expected.
*   Relevant queries returned expected document chunks.
*   Irrelevant queries were correctly identified by high distance scores.
*   The generation pipeline correctly constructs prompts and interacts with the mocked Ollama API.

### Status

Phase 3, Phase 4, and Phase 5 are complete. The project now has a stable and reliable pipeline for ingesting documents into a vector store, retrieving relevant information based on user queries, and generating answers using a local LLM. The foundation is solid for the next phase of development, which will focus on building a user interface.
