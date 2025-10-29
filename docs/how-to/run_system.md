# How to Run the CIVIX System

This document provides comprehensive instructions for setting up, running, and testing the CIVIX RAG system. It covers environment setup, automated testing, starting core services, and guidelines for manual testing.

## 1. Environment Setup

Before running any part of the system, ensure your Python virtual environment is active and all dependencies are installed.

1.  **Activate Virtual Environment:**
    ```bash
    source .venv/bin/activate
    ```
    (If you are using a different virtual environment name or path, adjust the command accordingly.)

2.  **Install Dependencies:**
    Ensure all required Python packages are installed.
    ```bash
    pip install -r requirements.txt
    ```

3.  **CPU-First Installation (Torch):**
    This project is configured for CPU-first operation. If you need to install PyTorch for CPU, use:
    ```bash
    pip install torch --index-url https://download.pytorch.org/whl/cpu
    ```
    If you require GPU support, install the appropriate CUDA-enabled PyTorch wheel separately (refer to the official PyTorch website).

4.  **Embedding Model:**
    The `all-MiniLM-L6-v2` embedding model is expected to be available locally at `./models/all-MiniLM-L6-v2`. This model is managed by Git LFS.

## 2. Automated Testing

The project includes a comprehensive `pytest` suite to ensure functional correctness and stability.

1.  **Run All Tests:**
    To run the entire test suite, you must set the `EMBED_MODEL` environment variable to the local path of the embedding model.
    ```bash
    source .venv/bin/activate
    EMBED_MODEL=./models/all-MiniLM-L6-v2 pytest
    ```
    *Expected Output:* All tests should pass (`8 passed`). If any tests fail, review the output for error messages.

## 3. Starting Core Services

The CIVIX system consists of a FastAPI backend and a Streamlit user interface. The generation pipeline also relies on a local Ollama server.

### 3.1 Start Ollama Server (Required for Generation)

Ensure Ollama is installed and running, and the `mistral` model is pulled.

1.  **Start Ollama:**
    ```bash
    ollama run mistral
    ```
    (If `mistral:instruct` is available but `mistral` is not, create an alias: `ollama cp mistral:instruct mistral`).

### 3.2 Start FastAPI Backend

The FastAPI backend provides the `/ingest` and `/query` API endpoints.

1.  **Start FastAPI Server:**
    It's recommended to run this in a separate terminal tab or as a background process.
    ```bash
    source .venv/bin/activate
    uvicorn ingestion_service:app --host 0.0.0.0 --port 8000 &
    ```
    *   **Access API Documentation:** Once running, you can access the interactive API documentation (Swagger UI) at `http://localhost:8000/docs`.
    *   **Access Metrics:** Prometheus metrics are exposed at `http://localhost:8000/metrics`.

### 3.3 Start Streamlit User Interface

The Streamlit UI provides a web-based interface for interacting with the RAG system.

1.  **Start Streamlit App:**
    Ensure the FastAPI backend is already running.
    ```bash
    source .venv/bin/activate
    streamlit run ui.py
    ```
    *   **Access UI:** The UI will typically open in your web browser at `http://localhost:8501`.

## 4. Manual Testing Guidelines

After starting all services, perform the following manual tests to ensure system coherence and integrity.

### 4.1 Ingestion Test

1.  **Navigate to Streamlit UI:** Open `http://localhost:8501` in your browser.
2.  **Upload a Document:**
    *   Locate the "Upload Document" section.
    *   Upload a sample PDF, DOCX, or TXT file (e.g., a simple text file with a few paragraphs).
    *   Verify that the ingestion process completes successfully (the UI should indicate completion or show a success message).
3.  **Verify Ingestion via API (Optional):**
    *   Open `http://localhost:8000/docs` (Swagger UI).
    *   Use the `/query` endpoint to search for terms you know are in the document you just uploaded.
    *   Verify that relevant chunks are returned.

### 4.2 Querying and Generation Test

1.  **Navigate to Streamlit UI:** Ensure you are on the main query interface.
2.  **Submit a Query:**
    *   Enter a natural language question related to the content of the document(s) you have ingested.
    *   Click "Submit Query".
3.  **Verify Results:**
    *   Check if a coherent answer is generated.
    *   Review the "Retrieved Chunks" section to ensure the context used for generation is relevant to your query.
    *   Adjust `top_k` and `rerank_k` sliders to observe changes in retrieval results.

### 4.3 Observability Check (Optional)

1.  **Check FastAPI Metrics:**
    *   Open `http://localhost:8000/metrics` in your browser.
    *   Look for metrics related to API requests, such as `http_requests_total` or `http_request_duration_seconds_bucket`, and observe if their values are increasing after you interact with the API/UI.
2.  **Check Tracing (if configured):**
    *   If you have a tracing collector (e.g., Jaeger) running and configured (as per `README.md` or `civix_method.md`), access its UI (e.g., `http://localhost:16686`).
    *   Search for traces related to `compliance-rag-api` and verify that requests from the UI to the FastAPI backend are being traced.

## 5. Troubleshooting

*   **"Embedding model could not be loaded."**: Ensure `EMBED_MODEL=./models/all-MiniLM-L6-v2` is set when running tests or the FastAPI server. Also, verify the model files are present in the specified directory.
*   **FastAPI/Streamlit connection issues**: Ensure both the FastAPI server and Streamlit app are running, and that Streamlit is configured to connect to the correct FastAPI address (default `http://localhost:8000`).
*   **Ollama generation issues**: Verify the Ollama server is running and the required model (e.g., `mistral`) is pulled. Check Ollama's logs for errors.
