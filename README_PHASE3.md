
# Phase 3: Vector Ingestion Pipeline

This document outlines how to set up and run the Phase-3 vector ingestion pipeline for the ComplianceRAG project.

## 1. Setup and Installation

First, create and activate a Python virtual environment. Then, install the required dependencies.

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install dependencies from requirements.txt
pip install -r requirements.txt
```

**Note on PyTorch:** The `requirements.txt` file specifies the CPU-only version of PyTorch. If you have a CUDA-enabled GPU and wish to use it, you can install the corresponding version of PyTorch by following the instructions on the [PyTorch website](https://pytorch.org/get-started/locally/).

## 2. Running the Ingestion Service

The ingestion service is a FastAPI application. You can run it using `uvicorn`.

```bash
# Run the FastAPI server
uvicorn ingestion_service:app --host 0.0.0.0 --port 8000 --reload
```

The service will be available at `http://localhost:8000`.

### Ingesting a Document

You can send a `POST` request with a file to the `/ingest/` endpoint to process a document.

```bash
curl -X POST -F "file=@/path/to/your/document.pdf" http://localhost:8000/ingest/
```

Supported file types are `.pdf`, `.docx`, and `.txt`.

## 3. Running Tests

Unit tests for the ingestion pipeline are located in the `tests/` directory and can be run using `pytest`.

```bash
# Run the test suite
pytest
```

The tests will:
1.  Create a sample document.
2.  Run the ingestion pipeline.
3.  Verify that the document is processed and stored correctly.
4.  Confirm that the caching mechanism is working.
5.  Clean up all generated data after the tests are complete.

