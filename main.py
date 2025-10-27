
import os
import uvicorn
import pypdf2
import docx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --------------------------------------------------------------------------
# Helper Functions
# --------------------------------------------------------------------------

def parse_document(file_path: str) -> str:
    """Extracts text content from PDF or DOCX files."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found at: {file_path}")

    _, extension = os.path.splitext(file_path)
    text = ""

    if extension.lower() == ".pdf":
        with open(file_path, "rb") as f:
            reader = pypdf2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
    elif extension.lower() == ".docx":
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    else:
        raise ValueError(f"Unsupported file type: {extension}")

    return text

# --------------------------------------------------------------------------
# Core Service Logic
# --------------------------------------------------------------------------

class CivixRAGService:
    """
    Handles the core logic for document ingestion and querying for CIVIX.
    """
    def __init__(self):
        print("Initializing CivixRAGService...")
        # Future connections to DBs and models will go here.
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

    def ingest_document(self, file_path: str):
        """Orchestrates the ingestion of a single document."""
        print(f"--- Starting ingestion for {file_path} ---")
        try:
            # 1. Parse Document
            text_content = parse_document(file_path)
            print(f"Successfully parsed {len(text_content)} characters.")

            # 2. Chunk Text
            chunks = self.text_splitter.split_text(text_content)
            print(f"Split text into {len(chunks)} chunks.")

            # 3. Embed & Store (to be implemented in Phase 3)
            print("Next step: Embedding and storing chunks.")

            print(f"--- Finished ingestion for {file_path} ---")
            return True
        except Exception as e:
            print(f"Error during ingestion: {e}")
            return False

# --------------------------------------------------------------------------
# FastAPI Application
# --------------------------------------------------------------------------

app = FastAPI(
    title="CIVIX RAG API",
    description="API for ingesting documents and answering compliance questions.",
    version="0.1.0",
)

rag_service = CivixRAGService()

# --- Pydantic Models ---

class IngestRequest(BaseModel):
    file_path: str = Field(..., description="The absolute path to the document to ingest.")

class IngestResponse(BaseModel):
    success: bool
    message: str

# --- API Endpoints ---

@app.get("/", tags=["Health Check"])
def root():
    """A simple health check endpoint."""
    return {"message": "CIVIX RAG API is running."}

@app.post("/ingest", response_model=IngestResponse, tags=["Ingestion"])
def ingest_endpoint(request: IngestRequest):
    """Endpoint to ingest a document."""
    success = rag_service.ingest_document(request.file_path)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to ingest document.")
    return IngestResponse(success=True, message=f"Successfully initiated ingestion for {request.file_path}")


# --- Main execution ---

if __name__ == "__main__":
    print("Starting FastAPI server for CIVIX...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
