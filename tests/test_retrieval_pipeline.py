

import os
import shutil
import pytest
from pathlib import Path

# Make the src directory available for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.processor import ingest_document, CHROMA_DIR, INGESTION_MANIFEST_PATH, EMBED_CACHE_DIR
from src.retrieval.retriever import query_collection

import chromadb

# --- Test Fixtures ---

@pytest.fixture(scope="module")
def setup_and_teardown_retrieval_test(tmp_path_factory):
    """Sets up the data for a retrieval test and cleans up afterward."""
    # --- Setup ---
    # Use a unique ChromaDB directory for each test module
    temp_chroma_dir = tmp_path_factory.mktemp("chroma_retrieval_test")
    client = chromadb.PersistentClient(path=str(temp_chroma_dir))

    # Create multiple dummy documents to ingest for re-ranking scenarios
    fixtures_dir = Path(__file__).parent / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)

    doc1_path = fixtures_dir / "retrieval_test_doc1.txt"
    doc1_content = "The penalty for late filing of tax returns is a fine of $100. This fine can be appealed under special circumstances."
    doc1_path.write_text(doc1_content)

    doc2_path = fixtures_dir / "retrieval_test_doc2.txt"
    doc2_content = "Tax regulations require all businesses to file their returns by April 15th. Extensions are available upon request."
    doc2_path.write_text(doc2_content)

    doc3_path = fixtures_dir / "retrieval_test_doc3.txt"
    doc3_content = "Appeals for financial penalties must be submitted within 30 days of the penalty notice. Legal counsel is recommended for complex cases."
    doc3_path.write_text(doc3_content)

    # Ingest the documents using the test client
    ingest_document(str(doc1_path), "retrieval_test_doc1", chroma_client=client)
    ingest_document(str(doc2_path), "retrieval_test_doc2", chroma_client=client)
    ingest_document(str(doc3_path), "retrieval_test_doc3", chroma_client=client)

    yield client # Yield the client for the tests to use

    # --- Teardown ---
    # Clean up the temporary ChromaDB directory
    if Path(temp_chroma_dir).exists():
        shutil.rmtree(temp_chroma_dir)
    if INGESTION_MANIFEST_PATH.exists():
        os.remove(INGESTION_MANIFEST_PATH)
    if EMBED_CACHE_DIR.exists():
        shutil.rmtree(EMBED_CACHE_DIR)
    if doc1_path.exists():
        os.remove(doc1_path)
    if doc2_path.exists():
        os.remove(doc2_path)
    if doc3_path.exists():
        os.remove(doc3_path)

# --- Test Cases ---

def test_retrieval_success(setup_and_teardown_retrieval_test):
    """Tests that a relevant query returns the correct document chunk."""
    # Arrange
    client = setup_and_teardown_retrieval_test
    query = "What is the penalty for late tax filing?"

    # Act
    # top_k here refers to the initial retrieval count, rerank_k is the final count
    results = query_collection(query_text=query, top_k=5, rerank_k=1, chroma_client=client)

    # Assert
    assert len(results) == 1 # Expecting 1 result after re-ranking
    top_result = results[0]
    assert "penalty for late filing" in top_result["document"]
    assert top_result["metadata"]["doc_id"] == "retrieval_test_doc1" # This document is most relevant

def test_retrieval_no_results(setup_and_teardown_retrieval_test):
    """Tests that an irrelevant query returns no results or results with high distance."""
    # Arrange
    client = setup_and_teardown_retrieval_test
    query = "What is the capital of Mars?"

    # Act
    results = query_collection(query_text=query, top_k=5, rerank_k=1, chroma_client=client)

    # Assert
    # An irrelevant query should either return no results, or results with a high
    # distance score. For cosine distance, a score > 0.8 is a very bad match.
    assert not results or results[0]["distance"] > 0.8

def test_retrieval_with_reranking(setup_and_teardown_retrieval_test):
    """Tests that re-ranking correctly prioritizes more relevant chunks."""
    # Arrange
    client = setup_and_teardown_retrieval_test
    # Query that has elements in doc1 and doc3, but is more strongly related to doc3
    query = "How do I appeal a financial penalty?"

    # Act
    # Retrieve more chunks initially (e.g., 5) and re-rank to a smaller set (e.g., 2)
    results = query_collection(query_text=query, top_k=5, rerank_k=2, chroma_client=client)

    # Assert
    assert len(results) == 2 # Expecting 2 results after re-ranking

    # Verify that the most relevant document (doc3) is among the top re-ranked results
    # and ideally is the first one.
    assert "Appeals for financial penalties" in results[0]["document"]
    assert results[0]["metadata"]["doc_id"] == "retrieval_test_doc3"

    # Also check that doc1, which mentions appeals, is also present if it's the second most relevant
    assert "penalty for late filing" in results[1]["document"]
    assert results[1]["metadata"]["doc_id"] == "retrieval_test_doc1"

