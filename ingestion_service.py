
import os
import shutil
import uuid
import logging
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from starlette.responses import JSONResponse

# It's good practice to set up a proper module structure.
# We assume the script is run from the project root.
import sys
sys.path.append(str(Path(__file__).parent))

from src.utils.logging_config import setup_logging
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
async def ingest_file(file: UploadFile = File(...)):
    """
    Receives a document, saves it temporarily, and triggers the ingestion pipeline.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file name provided.")

    # Generate a unique doc_id based on the filename
    # In a real system, you might want a more robust way to generate or receive this
    doc_id = Path(file.filename).stem

    # Save the uploaded file to a temporary path
    temp_path = UPLOAD_DIR / f"{uuid.uuid4().hex}_{file.filename}"
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logging.info(f"File '{file.filename}' uploaded to '{temp_path}'. Starting ingestion.")
        
        # Trigger the ingestion process
        report = ingest_document(str(temp_path), doc_id)
        
        if report.get("status") == "failed":
            raise HTTPException(status_code=500, detail=report)
            
        return JSONResponse(
            status_code=200,
            content={"message": f"Successfully ingested {file.filename}", "report": report}
        )

    except HTTPException as http_exc:
        # Re-raise HTTP exceptions to let FastAPI handle them
        raise http_exc
    except Exception as e:
        logging.error(f"An unexpected error occurred during ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")
    finally:
        # Clean up the uploaded file
        if temp_path.exists():
            os.remove(temp_path)
        
        # Close the uploaded file's stream
        await file.close()

@app.post("/query/")
def query(request: QueryRequest):
    """
    Receives a query, retrieves and re-ranks relevant document chunks, and generates an answer.
    """
    try:
        logging.info(f"Received query: {request.query_text}, initial_top_k: {request.top_k}, rerank_k: {request.rerank_k}")
        
        # query_collection now takes top_k as initial retrieval count and rerank_k for final count
        retrieved_chunks = query_collection(
            query_text=request.query_text,
            top_k=request.top_k, # This is the initial_retrieval_k for query_collection
            rerank_k=request.rerank_k # This is the final number of chunks after re-ranking
        )
        
        if not retrieved_chunks:
            return JSONResponse(
                status_code=404,
                content={"message": "No relevant documents found for retrieval."}
            )

        generated_answer = generate_answer(query=request.query_text, retrieved_chunks=retrieved_chunks)

        return {
            "query": request.query_text,
            "answer": generated_answer,
            "retrieved_chunks": retrieved_chunks # Optionally return chunks for context/debugging
        }
    except Exception as e:
        logging.error(f"An error occurred during query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")

if __name__ == "__main__":
    import uvicorn
    # logging is already configured by setup_logging()
    uvicorn.run(app, host="0.0.0.0", port=8000)
