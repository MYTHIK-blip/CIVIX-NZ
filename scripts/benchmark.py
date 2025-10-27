import httpx
import json
import time
import os

FASTAPI_HOST = os.getenv("FASTAPI_HOST", "localhost")
FASTAPI_PORT = os.getenv("FASTAPI_PORT", "8000")
FASTAPI_URL = f"http://{FASTAPI_HOST}:{FASTAPI_PORT}/"

DATA_DIR = "/home/mythik/projects/CIVIX/data"
EVAL_DATASET_PATH = os.path.join(DATA_DIR, "evaluation_dataset.json")
SOURCE_DOC_PATH = os.path.join(DATA_DIR, "gdpr_document.txt")

async def ingest_document(client: httpx.AsyncClient, file_path: str):
    """Ingests a document into the RAG system."""
    print(f"Ingesting document: {file_path}")
    print(f"Attempting to POST to: {FASTAPI_URL}ingest/")
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "text/plain")}
        response = await client.post(f"{FASTAPI_URL}ingest/", files=files, timeout=60.0)
        response.raise_for_status()
        print(f"Ingestion successful: {response.json()}")

async def query_rag_system(client: httpx.AsyncClient, query_text: str, top_k: int = 5, rerank_k: int = 3):
    """Queries the RAG system and returns the response."""
    print(f"Querying RAG system with URL: {FASTAPI_URL}query/")
    payload = {"query_text": query_text, "top_k": top_k, "rerank_k": rerank_k}
    start_time = time.perf_counter()
    response = await client.post(f"{FASTAPI_URL}query/", json=payload, timeout=60.0)
    end_time = time.perf_counter()
    response.raise_for_status()
    return response.json(), (end_time - start_time)

async def run_benchmark():
    """Runs the RAG system benchmark."""
    results = []
    async with httpx.AsyncClient() as client:
        # 1. Ingest source documents
        try:
            await ingest_document(client, SOURCE_DOC_PATH)
        except httpx.HTTPStatusError as e:
            print(f"Error during ingestion: {e.response.status_code} - {e.response.text}")
            return

        # 2. Load evaluation dataset
        with open(EVAL_DATASET_PATH, "r") as f:
            eval_dataset = json.load(f)

        # 3. Run queries and evaluate
        for entry in eval_dataset:
            query_id = entry["query_id"]
            query_text = entry["query_text"]
            gold_answer = entry["gold_answer"]
            relevant_chunks = entry["relevant_document_chunks"]

            print(f"Running query: {query_text}")
            try:
                rag_response, latency = await query_rag_system(client, query_text)
                generated_answer = rag_response.get("answer", "")
                retrieved_chunks = rag_response.get("retrieved_chunks", [])

                # Basic evaluation (can be expanded)
                # For now, just check if gold answer is somewhat contained in generated answer
                # And if relevant chunks are among retrieved chunks
                answer_match = gold_answer.lower() in generated_answer.lower()
                retrieval_success = any(
                    rc["chunk_text"].lower() in [c["document"].lower() for c in retrieved_chunks]
                    for rc in relevant_chunks
                )

                results.append({
                    "query_id": query_id,
                    "query_text": query_text,
                    "gold_answer": gold_answer,
                    "generated_answer": generated_answer,
                    "latency": latency,
                    "answer_match": answer_match,
                    "retrieval_success": retrieval_success,
                    "retrieved_chunks_count": len(retrieved_chunks)
                })
                print(f"  Generated Answer: {generated_answer[:100]}...")
                print(f"  Latency: {latency:.4f}s, Answer Match: {answer_match}, Retrieval Success: {retrieval_success}")

            except httpx.HTTPStatusError as e:
                print(f"Error during query {query_id}: {e.response.text}")
                results.append({
                    "query_id": query_id,
                    "query_text": query_text,
                    "error": str(e),
                    "latency": None,
                    "answer_match": False,
                    "retrieval_success": False
                })
            except Exception as e:
                print(f"An unexpected error occurred for query {query_id}: {e}")
                results.append({
                    "query_id": query_id,
                    "query_text": query_text,
                    "error": str(e),
                    "latency": None,
                    "answer_match": False,
                    "retrieval_success": False
                })

    print("\n--- Benchmark Results ---")
    for res in results:
        print(f"Query ID: {res['query_id']}")
        print(f"  Query: {res['query_text']}")
        print(f"  Latency: {res['latency']:.4f}s" if res.get('latency') is not None else "  Latency: N/A")
        print(f"  Answer Match (Gold in Generated): {res.get('answer_match', 'N/A')}")
        print(f"  Retrieval Success (Relevant Chunk Retrieved): {res.get('retrieval_success', 'N/A')}")
        print(f"  Retrieved Chunks Count: {res.get('retrieved_chunks_count', 'N/A')}")
        if res.get("error"):
            print(f"  Error: {res['error']}")
        print("-" * 20)

    # Calculate overall metrics
    total_queries = len(results)
    successful_queries = sum(1 for r in results if r.get("latency") is not None)
    avg_latency = sum(r["latency"] for r in results if r.get("latency") is not None) / successful_queries if successful_queries > 0 else 0
    answer_match_rate = sum(1 for r in results if r.get("answer_match")) / total_queries if total_queries > 0 else 0
    retrieval_success_rate = sum(1 for r in results if r.get("retrieval_success")) / total_queries if total_queries > 0 else 0

    print("\n--- Overall Metrics ---")
    print(f"Total Queries: {total_queries}")
    print(f"Successful Queries: {successful_queries}")
    print(f"Average Latency: {avg_latency:.4f}s")
    print(f"Answer Match Rate: {answer_match_rate:.2%}")
    print(f"Retrieval Success Rate: {retrieval_success_rate:.2%}")


if __name__ == "__main__":
    import asyncio
    # Create scripts directory if it doesn't exist
    os.makedirs("scripts", exist_ok=True)
    asyncio.run(run_benchmark())