
import os
import shutil
import uuid
import logging
import time
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from pydantic import BaseModel
from starlette.responses import JSONResponse, PlainTextResponse

from prometheus_client import generate_latest

# It's good practice to set up a proper module structure.
# We assume the script is run from the project root.
import sys
sys.path.append(str(Path(__file__).parent))

from src.utils.logging_config import setup_logging
from src.utils.metrics import REQUEST_COUNT, REQUEST_LATENCY_SECONDS, IN_PROGRESS_REQUESTS, INGESTION_DURATION_SECONDS
from src.utils.tracing import setup_tracing, tracer
from src.ingestion.processor import ingest_document
from src.retrieval.retriever import query_collection
from src.generation.generator import generate_answer

# Setup structured logging as early as possible
setup_logging()

app = FastAPI(
    title="ComplianceRAG API",
    description="An API for ingesting and querying compliance documents.",
    version="1.1.0",
)

# Setup OpenTelemetry tracing
setup_tracing(app)

class QueryRequest(BaseModel):
    query_text: str
    top_k: int = 5 # This will be the initial retrieval count from ChromaDB
    rerank_k: int = 3 # This will be the final number of chunks after re-ranking

# Define a temporary directory for uploads
UPLOAD_DIR = Path("./data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/")
def read_root():
    """A simple endpoint to confirm the service is running."""
    return {"message": "ComplianceRAG Ingestion Service is running."}


@app.post("/ingest/")
async def ingest_file(request: Request, file: UploadFile = File(...)):
    """
    Receives a document, saves it temporarily, and triggers the ingestion pipeline.
    """
    method = request.method
    endpoint = "/ingest/"
    status_code = 500 # Default to error

    IN_PROGRESS_REQUESTS.labels(method=method, endpoint=endpoint).inc()
    start_time = time.time()

    doc_id = "unknown" # Default for logging

    try:
        if not file.filename:
            status_code = 400
            raise HTTPException(status_code=status_code, detail="No file name provided.")

        doc_id = Path(file.filename).stem # Update doc_id if filename exists

        temp_path = UPLOAD_DIR / f"{uuid.uuid4().hex}_{file.filename}"
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logging.info(f"File '{file.filename}' uploaded to '{temp_path}'. Starting ingestion.", extra={"doc_id": doc_id, "file_name": file.filename})
        
        report = ingest_document(str(temp_path), doc_id)
        
        if report.get("status") == "failed":
            status_code = 500
            raise HTTPException(status_code=status_code, detail=report)
            
        status_code = 200
        return JSONResponse(
            status_code=status_code,
            content={"message": f"Successfully ingested {file.filename}", "report": report}
        )

    except HTTPException as http_exc:
        status_code = http_exc.status_code
        raise http_exc
    except Exception as e:
        logging.error(f"An unexpected error occurred during ingestion: {e}", exc_info=True, extra={"doc_id": doc_id, "file_name": file.filename})
        status_code = 500
        raise HTTPException(status_code=status_code, detail=f"An internal error occurred: {e}")
    finally:
        IN_PROGRESS_REQUESTS.labels(method=method, endpoint=endpoint).dec()
        REQUEST_LATENCY_SECONDS.labels(method=method, endpoint=endpoint).observe(time.time() - start_time)
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
        
        if temp_path.exists():
            os.remove(temp_path)
        
        await file.close()

@app.post("/query/")
def query(request: Request, query_request: QueryRequest):
    """
    Receives a query, retrieves and re-ranks relevant document chunks, and generates an answer.
    """
    method = request.method
    endpoint = "/query/"
    status_code = 500 # Default to error

    IN_PROGRESS_REQUESTS.labels(method=method, endpoint=endpoint).inc()
    start_time = time.time()

    try:
        logging.info(f"Received query: {query_request.query_text}, initial_top_k: {query_request.top_k}, rerank_k: {query_request.rerank_k}",
                     extra={"query_text": query_request.query_text, "initial_top_k": query_request.top_k, "rerank_k": query_request.rerank_k})
        
        retrieved_chunks = query_collection(
            query_text=query_request.query_text,
            top_k=query_request.top_k,
            rerank_k=query_request.rerank_k
        )
        
        if not retrieved_chunks:
            status_code = 404
            return JSONResponse(
                status_code=status_code,
                content={"message": "No relevant documents found for retrieval."}
            )

        generated_answer = generate_answer(query=query_request.query_text, retrieved_chunks=retrieved_chunks)

        status_code = 200
        return {
            "query": query_request.query_text,
            "answer": generated_answer,
            "retrieved_chunks": retrieved_chunks
        }
    except Exception as e:
        logging.error(f"An error occurred during query: {e}", exc_info=True, extra={"query_text": query_request.query_text})
        status_code = 500
        raise HTTPException(status_code=status_code, detail=f"An internal error occurred: {e}")
    finally:
        IN_PROGRESS_REQUESTS.labels(method=method, endpoint=endpoint).dec()
        REQUEST_LATENCY_SECONDS.labels(method=method, endpoint=endpoint).observe(time.time() - start_time)
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()

@app.get("/metrics")
def get_metrics():
    """
    Exposes Prometheus metrics.
    """
    return PlainTextResponse(generate_latest().decode('utf-8'), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    # logging is already configured by setup_logging()
    uvicorn.run(app, host="0.0.0.0", port=8000)
