
import os
import json
import shutil
from pathlib import Path
import pytest
from pypdf import PdfWriter

import time

# Make the src directory available for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.processor import ingest_document, CHROMA_DIR, INGESTION_MANIFEST_PATH, EMBED_CACHE_DIR, COLLECTION_NAME
import chromadb

# --- Test Fixtures ---

@pytest.fixture(scope="module")
def sample_pdf_path() -> Path:
    """Creates a simple, text-only PDF for testing and returns its path."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)
    pdf_path = fixtures_dir / "sample_short.pdf"
    
    # Create a very simple PDF with one page of text
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792) # Standard letter size
    # This is a hacky way to add text with pypdf. A real scenario would use a real PDF.
    # For a robust solution, one might use reportlab or a similar library.
    # But for this test, we just need a file that pypdf can read.
    # As pypdf has trouble creating text, we will rely on the text extraction from a blank page being empty
    # and for the logic to handle it. Let's create a txt file instead for a positive test case.
    
    txt_path = fixtures_dir / "sample_short.txt"
    txt_path.write_text("This is a test document for the ingestion pipeline. It contains simple text.")

    yield txt_path # Yield the path to the txt file

    # Cleanup
    if txt_path.exists():
        os.remove(txt_path)

@pytest.fixture(autouse=True)
def cleanup_data():
    """Cleans up data directories before and after each test run."""
    # Before test
    # EphemeralClient handles its own temporary storage, so no need to clean CHROMA_DIR here.
    if INGESTION_MANIFEST_PATH.exists():
        os.remove(INGESTION_MANIFEST_PATH)
    if EMBED_CACHE_DIR.exists():
        shutil.rmtree(EMBED_CACHE_DIR)

    yield

    # After test
    if INGESTION_MANIFEST_PATH.exists():
        os.remove(INGESTION_MANIFEST_PATH)
    if EMBED_CACHE_DIR.exists():
        shutil.rmtree(EMBED_CACHE_DIR)

# --- Test Cases ---

def test_ingest_document_success(sample_pdf_path, tmp_path):
    """Tests a successful ingestion of a document."""
    # Arrange
    doc_id = "sample_short_doc"
    file_path = str(sample_pdf_path)
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma_ingest_success"))

    # Act
    report = ingest_document(file_path, doc_id, chroma_client=client)

    # Assert
    # 1. Report is successful
    assert report["status"] == "completed"
    assert report["doc_id"] == doc_id
    assert report["total_chunks"] > 0
    assert report["new_embeddings"] == report["total_chunks"]

    # 2. Manifest is updated
    assert INGESTION_MANIFEST_PATH.exists()
    with open(INGESTION_MANIFEST_PATH, "r") as f:
        manifest = json.load(f)
    
    assert doc_id in manifest
    assert manifest[doc_id]["status"] == "completed"
    assert len(manifest[doc_id]["chunks"]) == report["total_chunks"]

    # 3. ChromaDB collection is updated
    collection = client.get_collection(name=COLLECTION_NAME)
    assert collection.count() == report["total_chunks"]

    # 4. Embed cache is created
    assert EMBED_CACHE_DIR.exists()
    # Check that there is one .npy file per chunk
    cached_files = list(EMBED_CACHE_DIR.glob("*.npy"))
    assert len(cached_files) == report["total_chunks"]

    # --- Verification Output ---
    print("\n--- Test Verification Summary ---")
    print(f"Chroma collection '{COLLECTION_NAME}' count: {collection.count()}")
    
    # Print first 3 entries of the manifest
    manifest_subset = {k: manifest[k] for i, k in enumerate(manifest) if i < 3}
    print("Sample manifest.json content:")
    print(json.dumps(manifest_subset, indent=2))
    print("---------------------------------")

def test_ingestion_is_idempotent(sample_pdf_path, tmp_path):
    """Tests that re-ingesting the same document uses the cache and doesn't add duplicates."""
    # Arrange
    doc_id = "idempotent_test_doc"
    file_path = str(sample_pdf_path)
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma_idempotent"))

    # Act 1: First ingestion
    report1 = ingest_document(file_path, doc_id, chroma_client=client)
    time.sleep(1)
    
    # Assert 1: First run creates new embeddings
    assert report1["status"] == "completed"
    assert report1["new_embeddings"] > 0
    assert report1["cached_embeddings"] == 0
    
    collection = client.get_collection(name=COLLECTION_NAME)
    count_after_first_ingest = collection.count()
    assert count_after_first_ingest > 0

    # Act 2: Second ingestion of the same document
    report2 = ingest_document(file_path, doc_id, chroma_client=client)

    # Assert 2: Second run should use cache
    assert report2["status"] == "completed"
    assert report2["new_embeddings"] == 0 # Crucial check for caching
    assert report2["cached_embeddings"] == report1["total_chunks"]
    
    # Assert that the number of items in ChromaDB has not changed
    count_after_second_ingest = collection.count()
    assert count_after_second_ingest == count_after_first_ingest
