

import os
import hashlib
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import backoff
import chromadb
import numpy as np
import pypdf
import docx
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer

# Logging is configured globally by src.utils.logging_config
# No need for logging.basicConfig here.

# --- Constants and Configuration ---
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
DEVICE = os.getenv("COMPLIANCE_DEVICE", "cpu")
BATCH_SIZE = int(os.getenv("COMPLIANCE_BATCH", "64"))
CHROMA_DIR = os.getenv("CHROMA_DIR", "./data/chroma")
EMBED_CACHE_DIR = Path(os.getenv("EMBED_CACHE_DIR", "./data/embed_cache"))
INGESTION_MANIFEST_PATH = Path(os.getenv("INGESTION_MANIFEST_PATH", "./data/ingestion_manifest.json"))
COLLECTION_NAME = "compliance_chunks"

# --- Initialize Components ---
try:
    embedding_model = SentenceTransformer(EMBED_MODEL, device=DEVICE)
    # Using a tokenizer from the same model for chunking calculations
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(EMBED_MODEL)
    CHUNK_SIZE_TOKENS = 700
    CHUNK_OVERLAP_TOKENS = 120
    logging.info(f"Using token-based chunking with chunk size {CHUNK_SIZE_TOKENS} and overlap {CHUNK_OVERLAP_TOKENS}.")
    token_based_chunking = True
except (ImportError, OSError):
    logging.warning("Transformers library not found or model data missing. Falling back to character-based chunking.")
    CHUNK_SIZE_CHARS = 2800  # Approx. 700 tokens * 4 chars/token
    CHUNK_OVERLAP_CHARS = 480   # Approx. 120 tokens * 4 chars/token
    logging.info(f"Using character-based chunking with chunk size {CHUNK_SIZE_CHARS} and overlap {CHUNK_OVERLAP_CHARS}.")
    token_based_chunking = False
    tokenizer = None


# --- Helper Functions ---

def _parse_document(file_path: str) -> str:
    """Parses content from PDF, DOCX, or TXT files."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if path.suffix == ".pdf":
        reader = pypdf.PdfReader(path)
        return "\n".join([page.extract_text() for page in reader.pages])
    elif path.suffix == ".docx":
        doc = docx.Document(path)
        return "\n".join([para.text for para in doc.paragraphs])
    elif path.suffix == ".txt":
        return path.read_text(encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}")

def _chunk_text(text: str) -> List[Tuple[str, int, int]]:
    """Chunks text by tokens (if available) or characters."""
    if not token_based_chunking or not tokenizer:
        # Character-based fallback
        chunks = []
        for i in range(0, len(text), CHUNK_SIZE_CHARS - CHUNK_OVERLAP_CHARS):
            chunk = text[i:i + CHUNK_SIZE_CHARS]
            start, end = i, i + len(chunk)
            chunks.append((chunk, start, end))
        return chunks

    # Token-based chunking
    tokens = tokenizer.encode(text, add_special_tokens=False)
    chunks = []
    for i in range(0, len(tokens), CHUNK_SIZE_TOKENS - CHUNK_OVERLAP_TOKENS):
        token_chunk = tokens[i:i + CHUNK_SIZE_TOKENS]
        chunk_text = tokenizer.decode(token_chunk, skip_special_tokens=True)
        
        # This is an approximation of start/end char positions
        # A more robust solution might involve mapping tokens back to char indices
        start = text.find(chunk_text)
        if start == -1:
            # Fallback if decoded text isn't found directly (e.g. due to normalization)
            # This is a rough estimate.
            char_pos_est = int((i / len(tokens)) * len(text)) if len(tokens) > 0 else 0
            start = char_pos_est

        end = start + len(chunk_text)
        chunks.append((chunk_text, start, end))
    return chunks


def _get_chunk_hash(doc_id: str, chunk: str, start: int, end: int) -> str:
    """Computes a SHA256 hash for a chunk."""
    first_64_chars = chunk[:64]
    hash_input = f"{doc_id}:{start}:{end}:{first_64_chars}"
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

def _get_cached_embedding(chunk_hash: str) -> np.ndarray | None:
    """Retrieves a cached embedding if it exists."""
    cache_file = EMBED_CACHE_DIR / f"{chunk_hash}.npy"
    if cache_file.exists():
        logging.info(f"Cache hit for chunk {chunk_hash}")
        return np.load(cache_file)
    return None

def _cache_embedding(chunk_hash: str, embedding: np.ndarray):
    """Caches an embedding to disk."""
    EMBED_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = EMBED_CACHE_DIR / f"{chunk_hash}.npy"
    np.save(cache_file, embedding)

@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def _embed_batch(batch_texts: List[str]) -> List[np.ndarray]:
    """Embeds a batch of texts with retry logic."""
    logging.info(f"Embedding batch of size {len(batch_texts)}...")
    return embedding_model.encode(batch_texts, convert_to_numpy=True)

@backoff.on_exception(backoff.expo, Exception, max_tries=2)
def _upsert_to_chroma(collection, ids: List[str], embeddings: List[np.ndarray], metadatas: List[Dict], documents: List[str]):
    """Upserts a batch to ChromaDB with retry logic."""
    logging.info(f"Upserting batch of size {len(ids)} to ChromaDB...")
    collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)

def _update_manifest(manifest_data: Dict):
    """Writes updated data to the ingestion manifest."""
    INGESTION_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(INGESTION_MANIFEST_PATH, "w") as f:
        json.dump(manifest_data, f, indent=4)

# --- Main Ingestion Function ---

def ingest_document(file_path: str, doc_id: str, chroma_client: Union[chromadb.Client, None] = None) -> Dict[str, Any]:
    """
    Parses, chunks, embeds, and upserts a document into the vector store.
    
    Args:
        file_path: The absolute path to the document file.
        doc_id: A unique identifier for the document.

    Returns:
        A dictionary containing the ingestion report.
    """
    ingest_run_id = f"run_{uuid.uuid4().hex[:8]}"
    start_time = time.time()
    logging.info(f"[{ingest_run_id}] Starting ingestion for doc_id: {doc_id} from file: {file_path}")

    # Initialize ChromaDB client and collection here
    if chroma_client is None:
        chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    
    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    # Load existing manifest or create new one
    if INGESTION_MANIFEST_PATH.exists():
        with open(INGESTION_MANIFEST_PATH, "r") as f:
            manifest = json.load(f)
    else:
        manifest = {}

    if doc_id not in manifest:
        manifest[doc_id] = {"status": "processing", "chunks": {}}

    try:
        # 1. Parse Document
        text = _parse_document(file_path)
        if not text.strip():
            logging.warning(f"Document {doc_id} is empty or contains no extractable text.")
            manifest[doc_id]["status"] = "failed_empty"
            _update_manifest(manifest)
            return {"status": "failed", "reason": "empty document"}

        # 2. Chunk Text
        chunks = _chunk_text(text)
        logging.info(f"Document {doc_id} split into {len(chunks)} chunks.")

        # 3. & 4. Process chunks in batches (Hashing, Caching, Embedding)
        chunks_to_embed_texts = []
        chunks_to_embed_metadata = []
        
        all_chunk_hashes = []
        all_chunk_embeddings = []
        all_chunk_metadatas = []
        all_chunk_texts = []

        for chunk_text, start_pos, end_pos in chunks:
            all_chunk_texts.append(chunk_text)
            chunk_hash = _get_chunk_hash(doc_id, chunk_text, start_pos, end_pos)
            all_chunk_hashes.append(chunk_hash)

            cached_embedding = _get_cached_embedding(chunk_hash)
            
            metadata = {
                "doc_id": doc_id,
                "file_path": file_path,
                "start_char": start_pos,
                "end_char": end_pos,
                "chunk_hash": chunk_hash
            }
            all_chunk_metadatas.append(metadata)

            if cached_embedding is not None:
                all_chunk_embeddings.append(cached_embedding)
            else:
                chunks_to_embed_texts.append(chunk_text)
                chunks_to_embed_metadata.append(metadata)
        
        # 5. Batch Embed if necessary
        newly_embedded_count = len(chunks_to_embed_texts)
        if chunks_to_embed_texts:
            logging.info(f"Found {len(chunks_to_embed_texts)} chunks to embed.")
            
            generated_embeddings = []
            for i in range(0, len(chunks_to_embed_texts), BATCH_SIZE):
                batch_texts = chunks_to_embed_texts[i:i + BATCH_SIZE]
                batch_embeddings = _embed_batch(batch_texts)
                generated_embeddings.extend(batch_embeddings)

            # Cache new embeddings
            for i, embedding in enumerate(generated_embeddings):
                chunk_hash_to_cache = chunks_to_embed_metadata[i]["chunk_hash"]
                _cache_embedding(chunk_hash_to_cache, embedding)

            # Re-assemble all embeddings in the correct order
            embedding_map = {m["chunk_hash"]: e for m, e in zip(chunks_to_embed_metadata, generated_embeddings)}
            
            temp_embeddings = list(all_chunk_embeddings) # Start with cached ones
            all_chunk_embeddings = []
            cached_idx = 0
            for meta in all_chunk_metadatas:
                h = meta["chunk_hash"]
                if h in embedding_map:
                    all_chunk_embeddings.append(embedding_map[h])
                else:
                    all_chunk_embeddings.append(temp_embeddings[cached_idx])
                    cached_idx += 1

        # 6. Upsert into ChromaDB
        failed_upsert_hashes = set()
        if all_chunk_hashes:
            try:
                _upsert_to_chroma(collection, ids=all_chunk_hashes, embeddings=all_chunk_embeddings, metadatas=all_chunk_metadatas, documents=all_chunk_texts)
            except Exception as e:
                logging.error(f"Failed to upsert batch after retries: {e}")
                # If the whole batch fails, we mark them all as failed.
                # A more granular approach would check which ones succeeded before retry.
                failed_upsert_hashes.update(all_chunk_hashes)

        # 7. Update Manifest
        for i, chunk_hash in enumerate(all_chunk_hashes):
            status = "upsert_failed" if chunk_hash in failed_upsert_hashes else "completed"
            manifest[doc_id]["chunks"][chunk_hash] = {
                "status": status,
                "metadata": all_chunk_metadatas[i]
            }
        
        final_status = "completed_with_errors" if failed_upsert_hashes else "completed"
        manifest[doc_id]["status"] = final_status
        _update_manifest(manifest)

    except Exception as e:
        logging.error(f"[{ingest_run_id}] Ingestion failed for doc_id {doc_id}: {e}", exc_info=True)
        manifest[doc_id]["status"] = "failed"
        manifest[doc_id]["error_message"] = str(e)
        _update_manifest(manifest)
        return {"status": "failed", "reason": str(e)}

    # 8. Logging and Metrics
    elapsed_time = time.time() - start_time
    report = {
        "ingest_run_id": ingest_run_id,
        "doc_id": doc_id,
        "status": manifest[doc_id]["status"],
        "total_chunks": len(all_chunk_hashes),
        "new_embeddings": newly_embedded_count,
        "cached_embeddings": len(all_chunk_hashes) - newly_embedded_count,
        "elapsed_time_seconds": round(elapsed_time, 2),
        "failed_upserts": len(failed_upsert_hashes)
    }
    logging.info(f"[{ingest_run_id}] Ingestion finished for doc_id {doc_id}. Report: {report}")
    
    return report

