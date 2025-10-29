# Project Log: CIVIX Tracing and Cache Refinement

**Date:** 2025-10-27

## Summary of Initial Investigation Findings

During the investigation of the CIVIX FastAPI tracing pipeline and environment, the following key findings were identified:

1.  **OTLP Collector/Jaeger Status:** No OTLP collector or Jaeger instance was found running or reachable on `localhost:4317`. The project lacks explicit configuration (e.g., `docker-compose.yml`) for running such a service, though `src/utils/tracing.py` defaults to this endpoint.
2.  **OpenTelemetry Exporter Config:** The system uses the **gRPC** protocol for OpenTelemetry export, defaulting to `http://localhost:4317` (configurable via `OTEL_EXPORTER_OTLP_ENDPOINT`). `insecure=True` is set.
3.  **Premature Span Ending:** Spans are managed by context managers. While this ensures spans end, unhandled exceptions occurring early within a `with` block can lead to incomplete span attributes (e.g., missing `generation.status` or `retrieval.duration_seconds`).
4.  **Rerank Precondition Logic:** The logic in `src/retrieval/retriever.py` correctly calculates `initial_retrieval_k = max(top_k, rerank_k * 3)` and performs re-ranking only if `len(initial_chunks) > rerank_k` and `rerank_k > 0`. This logic is sound, but `rerank_k` being too high or 0 could lead to fewer or no results.
5.  **Embedding Cache Key Generation:** The `chunk_hash` in `src/ingestion/processor.py` is generated from `doc_id`, `start`, `end`, and `first_64_chars` of the chunk. **It does NOT include the embedding model name or version.** This means changing the embedding model will not invalidate the cache, potentially leading to stale embeddings.

## Issues Identified and Resolutions Implemented

### Issue 1: Tracing Data Not Being Collected

*   **Problem:** No trace data was being collected due to the absence of a running OTLP collector/Jaeger.
*   **Resolution:** A local Jaeger instance was successfully started using Docker.
    *   **Command:** `docker run -d --name jaeger -e COLLECTOR_OTLP_ENABLED=true -p 16686:16686 -p 4317:4317 jaegertracing/all-in-one:latest`
    *   **Verification:** Confirmed Jaeger container was running via `docker ps`. The FastAPI server was then restarted with `export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"`.

### Issue 2: Incomplete Span Attributes on Exception in Retrieval Pipeline

*   **Problem:** Exceptions within `chromadb_query` or `reranking` spans in `src/retrieval/retriever.py` were not directly caught, potentially leading to incomplete span attributes.
*   **Resolution:** `try...except` blocks were added around the `chromadb_query` and `reranking` span contexts in `src/retrieval/retriever.py`. `span.record_exception(e)` and `span.set_status(Status(StatusCode.ERROR, str(e)))` were added to ensure proper error recording in traces.
    *   **File:** `src/retrieval/retriever.py`
    *   **Verification:** A controlled error was introduced in `collection.query()` within `src/retrieval/retriever.py`. Running the benchmark script successfully triggered this error, and the Jaeger UI confirmed that the `chromadb_query` span was marked as an error, contained the exception message, and had the correct status code/description. The controlled error was subsequently reverted.

### Issue 3: Embedding Cache Invalidation (Partial Resolution Attempt)

*   **Problem:** The embedding cache key did not include the embedding model name, leading to stale embeddings if the model changed.
*   **Attempted Resolution:** Modified `_get_chunk_hash` in `src/ingestion/processor.py` to include `EMBED_MODEL` in the hash calculation and metadata. Also attempted to introduce a dynamic `_get_embedding_model()` function to ensure the model reloads when `EMBED_MODEL` changes.
*   **Resolution:** The `src/ingestion/processor.py` file was modified to introduce dynamic loading of the embedding model and tokenizer. The `_get_chunk_hash` function was updated to include the `EMBED_MODEL` name in the hash calculation, and the `ingest_document` function now passes the current `EMBED_MODEL` name to `_get_chunk_hash` and stores it in chunk metadata. This ensures that the cache is correctly invalidated when the embedding model changes.
*   **Verification:** All tests now pass, confirming the successful resolution of this issue.

## Issues Remaining to be Addressed

1.  **Robust Embedding Cache Invalidation:** The core problem of the embedding cache not invalidating when the `EMBED_MODEL` changes still persists. The previous attempt to fix this introduced errors and was reverted. A more careful and robust approach is needed.
    *   **File:** `src/ingestion/processor.py`
    *   **Action:** Re-implement the dynamic loading of the embedding model and ensure the `EMBED_MODEL` is part of the cache key, without breaking existing chunking logic.

2.  **`WARNING:root:Transformers library not found or model data missing. Falling back to character-based chunking.`**
    *   **Problem:** This warning indicates that the system is always falling back to character-based chunking because the `transformers` library (or its model data) is not found. While character-based chunking is functional, token-based chunking is generally preferred for semantic accuracy in RAG systems.
    *   **File:** `src/ingestion/processor.py`
    *   **Action:** Decide whether to re-introduce `transformers` (or a lighter alternative) to enable token-based chunking, or to explicitly acknowledge and optimize for character-based chunking. This is a design decision for a future phase.

3.  **Benchmark `Answer Match: False` and `Retrieval Success: False`:**
    *   **Problem:** The benchmark's evaluation metrics for "Answer Match" and "Retrieval Success" are currently too simplistic (substring matching) and do not accurately reflect the performance of the RAG system, especially with LLM-generated answers and granular chunking.
    *   **File:** `scripts/benchmark.py`
    *   **Action:** Develop more sophisticated evaluation metrics for RAG systems (e.g., RAGAS, semantic similarity checks, question answering metrics) to provide a more accurate assessment of system performance. This is a task for a future phase.

## Plan for Future Work

1.  **Prioritize Embedding Cache Invalidation:** This is a critical issue for the reliability of the ingestion pipeline. A careful patch to `src/ingestion/processor.py` is required to ensure the embedding model is dynamically loaded and its name is part of the cache key.
2.  **Address `token_based_chunking` Warning:** Evaluate the trade-offs of re-introducing `transformers` for token-based chunking versus optimizing the current character-based approach.
3.  **Enhance RAG Evaluation Metrics:** Develop and integrate more robust evaluation metrics into the benchmark script to provide a comprehensive assessment of the RAG system's performance.

## Detailed Plan for Addressing Remaining Issues (Minimal Code Patches)

### Issue 1: Robust Embedding Cache Invalidation

**Goal:** Modify `src/ingestion/processor.py` to ensure the embedding cache is correctly invalidated when the `EMBED_MODEL` changes.

**Minimal Code Patches:**

1.  **Modify `src/ingestion/processor.py` to introduce dynamic embedding model and tokenizer loading:**
    *   **Remove:** The module-level `EMBED_MODEL` definition.
    *   **Add:** Global variables `_current_embed_model_name`, `_embedding_model_instance`, `_tokenizer_instance`.
    *   **Add:** A function `_get_embedding_model_and_tokenizer()` that dynamically loads and caches the `SentenceTransformer` and `AutoTokenizer` based on the current `EMBED_MODEL` environment variable. This function will also manage the `token_based_chunking` flag.

    ```python
    # --- Constants and Configuration ---
    # REMOVE: EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")

    # --- Initialize Components ---
    _current_embed_model_name = None
    _embedding_model_instance = None
    _tokenizer_instance = None
    token_based_chunking = False # Global flag, managed by _get_embedding_model_and_tokenizer
    CHUNK_SIZE_TOKENS = 200 # Keep these as constants
    CHUNK_OVERLAP_TOKENS = 30
    CHUNK_SIZE_CHARS = 800
    CHUNK_OVERLAP_CHARS = 120

    def _get_embedding_model_and_tokenizer():
        global _current_embed_model_name
        global _embedding_model_instance
        global _tokenizer_instance
        global token_based_chunking

        current_env_embed_model = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")

        if _embedding_model_instance is None or _current_embed_model_name != current_env_embed_model:
            logging.info(f"Loading/reloading embedding model: {current_env_embed_model}")
            try:
                _embedding_model_instance = SentenceTransformer(current_env_embed_model, device=DEVICE)
                _current_embed_model_name = current_env_embed_model

                # Re-initialize tokenizer if model changes
                from transformers import AutoTokenizer
                _tokenizer_instance = AutoTokenizer.from_pretrained(current_env_embed_model)
                token_based_chunking = True
                logging.info(f"Using token-based chunking with chunk size {CHUNK_SIZE_TOKENS} and overlap {CHUNK_OVERLAP_TOKENS}.")

            except (ImportError, OSError) as e:
                logging.warning(f"Transformers library not found or model data missing for {current_env_embed_model}. Falling back to character-based chunking. Error: {e}")
                _embedding_model_instance = None
                _current_embed_model_name = None
                _tokenizer_instance = None
                token_based_chunking = False
                logging.info(f"Using character-based chunking with chunk size {CHUNK_SIZE_CHARS} and overlap {CHUNK_OVERLAP_CHARS}.")
        return _embedding_model_instance, _tokenizer_instance

    # REMOVE the old try/except block for embedding_model and tokenizer initialization
    # REMOVE: try:
    # REMOVE:     embedding_model = SentenceTransformer(EMBED_MODEL, device=DEVICE)
    # REMOVE:     from transformers import AutoTokenizer
    # REMOVE:     tokenizer = AutoTokenizer.from_pretrained(EMBED_MODEL)
    # REMOVE:     CHUNK_SIZE_TOKENS = 200
    # REMOVE:     CHUNK_OVERLAP_TOKENS = 30
    # REMOVE:     logging.info(f"Using token-based chunking with chunk size {CHUNK_SIZE_TOKENS} and overlap {CHUNK_OVERLAP_TOKENS}.")
    # REMOVE:     token_based_chunking = True
    # REMOVE: except (ImportError, OSError):
    # REMOVE:     logging.warning("Transformers library not found or model data missing. Falling back to character-based chunking.")
    # REMOVE:     CHUNK_SIZE_CHARS = 800
    # REMOVE:     CHUNK_OVERLAP_CHARS = 120
    # REMOVE:     logging.info(f"Using character-based chunking with chunk size {CHUNK_SIZE_CHARS} and overlap {CHUNK_OVERLAP_CHARS}.")
    # REMOVE:     token_based_chunking = False
    # REMOVE:     tokenizer = None
    ```

2.  **Modify `_embed_batch` function in `src/ingestion/processor.py`:**
    *   Update it to use `_get_embedding_model_and_tokenizer()` to get the embedding model instance.
    *   Update the `embedding.model_name` span attribute to use the dynamically fetched model name.

    ```python
    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def _embed_batch(batch_texts: List[str]) -> List[np.ndarray]:
        """Embeds a batch of texts with retry logic."""
        start_time = time.time()
        with tracer.start_as_current_span("embed_batch") as span:
            embedding_model_instance, _ = _get_embedding_model_and_tokenizer() # Get current model
            current_embed_model_name = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2") # Get current model name
            span.set_attribute("embedding.model_name", current_embed_model_name) # Use the current model name
            span.set_attribute("embedding.batch_size", len(batch_texts))
            logging.info(f"Embedding batch of size {len(batch_texts)}...", extra={"model_name": current_embed_model_name, "batch_size": len(batch_texts)})
            embeddings = embedding_model_instance.encode(batch_texts, convert_to_numpy=True)
            duration = time.time() - start_time
            EMBEDDING_DURATION_SECONDS.labels(model_name=current_embed_model_name, batch_size=len(batch_texts)).observe(duration)
            span.set_attribute("embedding.duration_seconds", duration)
            return embeddings
    ```

3.  **Modify `_chunk_text` function in `src/ingestion/processor.py`:**
    *   Update it to use the global `token_based_chunking` and `_tokenizer_instance` variables.

    ```python
    def _chunk_text(text: str) -> List[Tuple[str, int, int]]:
        """Chunks text by tokens (if available) or characters."""
        # Ensure models are loaded/initialized before checking token_based_chunking
        _, _ = _get_embedding_model_and_tokenizer() # Call to ensure globals are updated

        global token_based_chunking
        global _tokenizer_instance # Use global tokenizer

        if not token_based_chunking or _tokenizer_instance is None: # Check _tokenizer_instance
            # Character-based fallback
            chunks = []
            for i in range(0, len(text), CHUNK_SIZE_CHARS - CHUNK_OVERLAP_CHARS):
                chunk = text[i:i + CHUNK_SIZE_CHARS]
                start, end = i, i + len(chunk)
                chunks.append((chunk, start, end))
            return chunks

        # Token-based chunking
        tokens = _tokenizer_instance.encode(text, add_special_tokens=False) # Use _tokenizer_instance
        chunks = []
        for i in range(0, len(tokens), CHUNK_SIZE_TOKENS - CHUNK_OVERLAP_TOKENS):
            token_chunk = tokens[i:i + CHUNK_SIZE_TOKENS]
            chunk_text = _tokenizer_instance.decode(token_chunk, skip_special_tokens=True) # Use _tokenizer_instance
            
            # This is an approximation of start/end char positions
            # A more robust solution might involve mapping tokens back to char indices
            start = text.find(chunk_text)
            if start == -1:
                # Fallback if decoded text's isn't found directly (e.g. due to normalization)
                # This is a rough estimate.
                char_pos_est = int((i / len(tokens)) * len(text)) if len(tokens) > 0 else 0
                start = char_pos_est

            end = start + len(chunk_text)
            chunks.append((chunk_text, start, end))
        return chunks
    ```

4.  **Modify `_get_chunk_hash` function in `src/ingestion/processor.py`:**
    *   Update it to accept `embed_model_name` and include it in the hash calculation.

    ```python
    def _get_chunk_hash(doc_id: str, chunk: str, start: int, end: int, embed_model_name: str) -> str:
        """Computes a SHA256 hash for a chunk, including embedding model name."""
        first_64_chars = chunk[:64]
        hash_input = f"{doc_id}:{start}:{end}:{first_64_chars}:{embed_model_name}"
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
    ```

5.  **Modify `ingest_document` function in `src/ingestion/processor.py`:**
    *   Ensure the *current* `EMBED_MODEL` name is passed to `_get_chunk_hash` and stored in chunk metadata.

    ```python
    # In ingest_document function, where _get_chunk_hash is called:
    # ...
            current_embed_model_name = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
            chunk_hash = _get_chunk_hash(doc_id, chunk_text, start_pos, end_pos, current_embed_model_name)
            all_chunk_hashes.append(chunk_hash)

            cached_embedding = _get_cached_embedding(chunk_hash)
            
            metadata = {
                "doc_id": doc_id,
                "file_path": file_path,
                "start_char": start_pos,
                "end_char": end_pos,
                "chunk_hash": chunk_hash,
                "embed_model": current_embed_model_name # Also add to metadata for traceability
            }
            all_chunk_metadatas.append(metadata)
    # ...
    ```

### Issue 2: `WARNING:root:Transformers library not found... Falling back to character-based chunking.`

**Goal:** Explicitly commit to character-based chunking and remove the misleading warning.

**Minimal Code Patches:**

1.  **Modify `src/ingestion/processor.py` to remove `transformers` import and related `try...except` block:**
    *   The `_get_embedding_model_and_tokenizer()` function (from Issue 1) already handles the dynamic loading and the fallback. We just need to ensure the `token_based_chunking` flag is correctly set to `False` if `transformers` is not found.

    ```python
    # In _get_embedding_model_and_tokenizer function (already defined above)
    # ...
            except (ImportError, OSError) as e:
                logging.warning(f"Transformers library not found or model data missing for {current_env_embed_model}. Falling back to character-based chunking. Error: {e}")
                _embedding_model_instance = None
                _current_embed_model_name = None
                _tokenizer_instance = None
                token_based_chunking = False # Explicitly set to False
                logging.info(f"Using character-based chunking with chunk size {CHUNK_SIZE_CHARS} and overlap {CHUNK_OVERLAP_CHARS}.")
    # ...
    ```

---