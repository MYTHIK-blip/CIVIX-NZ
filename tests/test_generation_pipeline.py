

import os
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch
import json

# Make the src directory available for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.processor import ingest_document, CHROMA_DIR, INGESTION_MANIFEST_PATH, EMBED_CACHE_DIR
from src.retrieval.retriever import query_collection
from src.generation.generator import generate_answer
import chromadb

# --- Test Fixtures ---

@pytest.fixture(scope="module")
def setup_rag_test_data(tmp_path_factory):
    """Sets up the data for a RAG test (ingestion and retrieval) and cleans up afterward."""
    # Use a unique ChromaDB directory for each test module
    temp_chroma_dir = tmp_path_factory.mktemp("chroma_rag_test")
    client = chromadb.PersistentClient(path=str(temp_chroma_dir))

    # Create a dummy document to ingest
    fixtures_dir = Path(__file__).parent / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)
    doc_path = fixtures_dir / "rag_test_doc.txt"
    doc_content = "The capital of France is Paris. Paris is known for its Eiffel Tower. " \
                  "The official language of France is French."
    doc_path.write_text(doc_content)

    # Ingest the document using the test client
    ingest_report = ingest_document(str(doc_path), "rag_test_doc", chroma_client=client)
    assert ingest_report["status"] == "completed"
    assert ingest_report["total_chunks"] > 0

    yield client # Yield the client for the tests to use

    # --- Teardown ---
    # Clean up the temporary ChromaDB directory
    if Path(temp_chroma_dir).exists():
        shutil.rmtree(temp_chroma_dir)
    if INGESTION_MANIFEST_PATH.exists():
        os.remove(INGESTION_MANIFEST_PATH)
    if EMBED_CACHE_DIR.exists():
        shutil.rmtree(EMBED_CACHE_DIR)
    if doc_path.exists():
        os.remove(doc_path)

# --- Test Cases ---

def test_generate_answer_success(setup_rag_test_data):
    """Tests that the generation function produces a reasonable answer."""
    # Arrange
    client = setup_rag_test_data
    query = "What is the capital of France?"
    
    # Simulate retrieved chunks (normally from query_collection)
    # For this test, we'll use a simplified chunk that directly answers the question
    # In a real scenario, query_collection would be called first.
    retrieved_chunks = [
        {"document": "The capital of France is Paris.", "metadata": {"doc_id": "rag_test_doc"}}
    ]

    # Mock the httpx.post call to the Ollama API
    with patch('httpx.post') as mock_post:
        mock_response = mock_post.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "The capital of France is Paris."}
        mock_response.raise_for_status.return_value = None

        # Act
        generated_answer = generate_answer(query=query, retrieved_chunks=retrieved_chunks)

        # Assert
        assert "Paris" in generated_answer
        mock_post.assert_called_once() # Ensure the API was called

def test_generate_answer_no_chunks(setup_rag_test_data):
    """Tests that the generation function handles no retrieved chunks gracefully."""
    # Arrange
    client = setup_rag_test_data # Not directly used, but fixture provides cleanup
    query = "What is the capital of Germany?"
    retrieved_chunks = [] # No chunks provided

    # Act
    generated_answer = generate_answer(query=query, retrieved_chunks=retrieved_chunks)

    # Assert
    assert "couldn't find any relevant information" in generated_answer


def test_rag_full_pipeline_success(setup_rag_test_data):
    """Tests the full RAG pipeline: retrieval followed by generation."""
    # Arrange
    client = setup_rag_test_data
    query = "What is France known for?"

    # Mock the httpx.post call to the Ollama API
    with patch('httpx.post') as mock_post:
        mock_response = mock_post.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "France is known for its Eiffel Tower."}
        mock_response.raise_for_status.return_value = None

        # Act
        # 1. Retrieve chunks
        retrieved_chunks = query_collection(query_text=query, top_k=1, chroma_client=client)
        assert len(retrieved_chunks) > 0
        assert "eiffel tower" in retrieved_chunks[0]["document"].lower()

        # 2. Generate answer
        generated_answer = generate_answer(query=query, retrieved_chunks=retrieved_chunks)

        # Assert
        assert "Eiffel Tower" in generated_answer
        mock_post.assert_called_once() # Ensure the API was called

