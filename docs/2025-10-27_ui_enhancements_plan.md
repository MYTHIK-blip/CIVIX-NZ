# Project Log: ComplianceRAG

**Date:** 2025-10-27

## Subject: Phase 9: User Interface Enhancements - Planning

### Summary

This document outlines the plan for Phase 9, focusing on improving the user experience and functionality of the Streamlit UI. This phase aims to make the ComplianceRAG system more interactive and user-friendly by adding key features such as document upload, query history, and enhanced display options.

### Goal

Improve the user experience and functionality of the Streamlit UI by adding key features that enhance interaction with the ComplianceRAG system.

### Key Features

1.  **Document Upload via UI:**
    *   Allow users to upload PDF, DOCX, or TXT files directly through the Streamlit interface.
    *   Integrate this with the `/ingest` endpoint of the FastAPI backend.
    *   Provide feedback on ingestion status.

2.  **Query History:**
    *   Display a history of previous queries and their corresponding answers/retrieved chunks within the UI session.
    *   Allow users to re-run or inspect past queries.

3.  **Enhanced Display of Retrieved Chunks:**
    *   Improve the readability and organization of retrieved chunks.
    *   Potentially highlight query terms within the chunks.
    *   Display source document information more prominently (e.g., filename, page number if available in metadata).

4.  **Configuration Options in UI:**
    *   Allow users to adjust `top_k` (initial retrieval count) and `rerank_k` (final re-ranked count) directly from the UI.
    *   Potentially allow selection of the Ollama model if multiple are available (though this might be more complex to manage if models need to be loaded/unloaded dynamically).

### Impacted Modules

*   `ui.py` (Streamlit application)
*   `ingestion_service.py` (The `/ingest` endpoint is already there, but UI integration will drive its use)

### Implementation Steps

1.  **Document Upload:**
    *   Add `st.file_uploader` to `ui.py`.
    *   Implement logic to send uploaded files to the FastAPI `/ingest` endpoint using `httpx`.
    *   Display ingestion reports/status.
2.  **Query History:**
    *   Use Streamlit's `st.session_state` to store query history.
    *   Render the history in a collapsible section or similar.
3.  **Enhanced Chunk Display:**
    *   Modify the display logic in `ui.py` to format chunks better.
    *   Explore libraries for text highlighting if needed.
4.  **Configuration Options:**
    *   Add `st.slider` or `st.number_input` widgets for `top_k` and `rerank_k`.
    *   Pass these values to the `/query` endpoint.

### Deliverables

*   Updated `ui.py` with new features.
*   Updated `README.md` with instructions for new UI features.
*   A new log entry in `docs/` detailing the implementation of UI enhancements.

### Status

This document serves as the planning phase for Phase 9. Implementation will commence upon approval.
