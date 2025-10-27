
import os
import logging
import chromadb
import time
import hashlib
from sentence_transformers import SentenceTransformer, CrossEncoder
from typing import List, Dict, Any, Union

from src.utils.tracing import tracer
from src.utils.metrics import RETRIEVAL_DURATION_SECONDS, RERANKING_DURATION_SECONDS, CHROMA_QUERY_DURATION_SECONDS

# --- Constants and Configuration ---
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
RERANK_MODEL = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
DEVICE = os.getenv("COMPLIANCE_DEVICE", "cpu")
CHROMA_DIR = os.getenv("CHROMA_DIR", "./data/chroma")
COLLECTION_NAME = "compliance_chunks"

# --- Initialize Components ---
# Embedding model is loaded once at module level for efficiency.
try:
    embedding_model = SentenceTransformer(EMBED_MODEL, device=DEVICE)
except Exception as e:
    logging.error(f"Failed to load SentenceTransformer model: {e}", exc_info=True)
    embedding_model = None

# Re-ranking model is loaded once at module level for efficiency.
try:
    reranker_model = CrossEncoder(RERANK_MODEL, device=DEVICE)
except Exception as e:
    logging.error(f"Failed to load CrossEncoder model: {e}", exc_info=True)
    reranker_model = None

# --- Retrieval Function ---

def query_collection(query_text: str, top_k: int = 5, rerank_k: int = 3, chroma_client: Union[chromadb.Client, None] = None) -> List[Dict[str, Any]]:
    """
    Embeds a query, retrieves an initial set of relevant chunks,
    re-ranks them, and returns the top_k most relevant chunks.

    Args:
        query_text: The user's query.
        top_k: The number of initial results to retrieve from ChromaDB before re-ranking.
        rerank_k: The number of results to return after re-ranking.
        chroma_client: An optional ChromaDB client instance.

    Returns:
        A list of dictionaries, where each dictionary represents a retrieved and re-ranked chunk.
    """
    start_time = time.time()
    query_text_hash = hashlib.sha256(query_text.encode('utf-8')).hexdigest()

    with tracer.start_as_current_span("query_collection") as span:
        span.set_attribute("query.text_hash", query_text_hash)
        span.set_attribute("query.initial_top_k", top_k)
        span.set_attribute("query.rerank_k", rerank_k)

        if not embedding_model:
            raise RuntimeError("Embedding model is not available.")
        if not reranker_model:
            raise RuntimeError("Re-ranking model is not available.")

        try:
            if chroma_client is None:
                # This is the production path: create a new persistent client.
                chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
            
            collection = chroma_client.get_collection(name=COLLECTION_NAME)
        except Exception as e:
            logging.error(f"Failed to connect to ChromaDB collection '{COLLECTION_NAME}': {e}", exc_info=True)
            raise RuntimeError(f"ChromaDB collection '{COLLECTION_NAME}' is not available.")

        logging.info(f"Embedding query: '{query_text[:50]}...'", extra={"query_text_hash": query_text_hash})
        query_embedding = embedding_model.encode(query_text, convert_to_numpy=True)

        # Retrieve a larger set of candidates for re-ranking
        initial_retrieval_k = max(top_k, rerank_k * 3) # Retrieve at least 3x the rerank_k, or top_k if larger
        logging.info(f"Querying collection '{COLLECTION_NAME}' for initial {initial_retrieval_k} results.", extra={"initial_retrieval_k": initial_retrieval_k})
        
        chroma_query_start_time = time.time()
        with tracer.start_as_current_span("chromadb_query") as chroma_span:
            chroma_span.set_attribute("chroma.n_results", initial_retrieval_k)
            results = collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=initial_retrieval_k,
                include=["metadatas", "documents", "distances"]
            )
            chroma_query_duration = time.time() - chroma_query_start_time
            CHROMA_QUERY_DURATION_SECONDS.observe(chroma_query_duration)
            chroma_span.set_attribute("chroma.query_duration_seconds", chroma_query_duration)

    if not results or not results.get('ids') or not results['ids'][0]:
        return []

    # Re-format the initial results
    initial_chunks = []
    ids = results['ids'][0]
    distances = results['distances'][0]
    metadatas = results['metadatas'][0]
    documents = results['documents'][0]

    for i in range(len(ids)):
        initial_chunks.append({
            "id": ids[i],
            "distance": distances[i],
            "document": documents[i],
            "metadata": metadatas[i]
        })

    # Perform re-ranking if we have enough chunks and rerank_k is meaningful
    if len(initial_chunks) > rerank_k and rerank_k > 0:
        reranking_start_time = time.time()
        with tracer.start_as_current_span("reranking") as rerank_span:
            rerank_span.set_attribute("reranking.initial_count", len(initial_chunks))
            rerank_span.set_attribute("reranking.final_count", rerank_k)
            rerank_span.set_attribute("reranking.model_name", RERANK_MODEL)
            logging.info(f"Performing re-ranking on {len(initial_chunks)} chunks to select top {rerank_k}.", extra={"initial_chunks_count": len(initial_chunks), "rerank_k": rerank_k})
            sentence_pairs = [[query_text, chunk["document"]] for chunk in initial_chunks]
            re_rank_scores = reranker_model.predict(sentence_pairs)

            # Combine chunks with their scores and sort
            scored_chunks = sorted(
                zip(initial_chunks, re_rank_scores),
                key=lambda x: x[1],
                reverse=True
            )
            
            # Select the top rerank_k chunks
            retrieved_chunks = [chunk for chunk, score in scored_chunks[:rerank_k]]
            reranking_duration = time.time() - reranking_start_time
            RERANKING_DURATION_SECONDS.labels(query_text_hash=query_text_hash).observe(reranking_duration)
            rerank_span.set_attribute("reranking.duration_seconds", reranking_duration)
    else:
        logging.info("Skipping re-ranking (not enough chunks or rerank_k is 0).", extra={"initial_chunks_count": len(initial_chunks), "rerank_k": rerank_k})
        retrieved_chunks = initial_chunks[:rerank_k] # Just take the top rerank_k from initial retrieval

    RETRIEVAL_DURATION_SECONDS.labels(query_text_hash=query_text_hash).observe(time.time() - start_time)
    span.set_attribute("retrieval.duration_seconds", time.time() - start_time)
    return retrieved_chunks
