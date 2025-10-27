import streamlit as st
import httpx
import os

# Configuration for the FastAPI backend
FASTAPI_HOST = os.getenv("FASTAPI_HOST", "http://localhost")
FASTAPI_PORT = os.getenv("FASTAPI_PORT", "8000")
FASTAPI_URL = f"{FASTAPI_HOST}:{FASTAPI_PORT}"

st.set_page_config(page_title="ComplianceRAG UI", layout="wide")

st.title("ComplianceRAG: Ask Your Documents")

# --- Document Ingestion Section ---
st.header("Document Ingestion")
uploaded_file = st.file_uploader("Upload a document (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])

if uploaded_file is not None:
    if st.button("Ingest Document"):
        with st.spinner(f"Ingesting {uploaded_file.name}..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
ingest_response = httpx.post(f"{FASTAPI_URL}/ingest/", files=files, timeout=300.0)
ingest_response.raise_for_status()
ingest_result = ingest_response.json()
st.success(f"Successfully ingested {uploaded_file.name}!")
st.json(ingest_result)
            except httpx.RequestError as e:
                st.error(f"Network error connecting to FastAPI backend for ingestion: {e}")
            except httpx.HTTPStatusError as e:
                st.error(f"Error from FastAPI backend during ingestion: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                st.error(f"An unexpected error occurred during ingestion: {e}")
st.markdown("---")

# --- Query Section ---
st.header("Ask Your Documents")

# Initialize session state for query history
if "query_history" not in st.session_state:
    st.session_state.query_history = []

# User input for the query
query_text = st.text_area("Enter your question here:", height=100, key="query_input")
col1, col2 = st.columns(2)
with col1:
    top_k = st.slider("Initial chunks to retrieve (for re-ranking candidates):", min_value=1, max_value=10, value=5, key="top_k_slider")
with col2:
    rerank_k = st.slider("Final chunks after re-ranking:", min_value=1, max_value=top_k, value=3, key="rerank_k_slider")


if st.button("Get Answer", key="get_answer_button"):
    if query_text:
        with st.spinner("Searching and generating answer..."):
            try:
                response = httpx.post(
                    f"{FASTAPI_URL}/query",
                    json={"query_text": query_text, "top_k": top_k, "rerank_k": rerank_k},
                    timeout=300.0 # Increased timeout for potentially long generation
                )
                response.raise_for_status() # Raise an exception for 4xx or 5xx status codes
                result = response.json()

                # Store query and result in history
                st.session_state.query_history.append({
                    "query": query_text,
                    "top_k": top_k,
                    "rerank_k": rerank_k,
                    "answer": result.get("answer", "No answer generated."),
                    "retrieved_chunks": result.get("retrieved_chunks", [])
                })
                
                st.subheader("Generated Answer:")
                st.write(result.get("answer", "No answer generated."))

                st.subheader("Retrieved Context:")
                if result.get("retrieved_chunks"):
                    for i, chunk in enumerate(result["retrieved_chunks"]):
                        st.markdown(f"**Chunk {i+1}:**")
                        st.write(chunk.get("document", "N/A"))
                        if chunk.get("metadata"):
                            st.json(chunk["metadata"])
                        st.markdown("---")
                else:
                    st.info("No relevant chunks retrieved.")

            except httpx.RequestError as e:
                st.error(f"Network error connecting to FastAPI backend: {e}")
            except httpx.HTTPStatusError as e:
                st.error(f"Error from FastAPI backend: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")
    else:
        st.warning("Please enter a question to get an answer.")

st.markdown("---")

# --- Query History Section ---
if st.session_state.query_history:
    st.header("Query History")
    with st.expander("View Past Queries"):
        for i, entry in enumerate(reversed(st.session_state.query_history)): # Show most recent first
            st.markdown(f"**Query {len(st.session_state.query_history) - i}:** {entry['query']}")
            st.markdown(f"**Answer:** {entry['answer']}")
            if st.checkbox(f"Show Context for Query {len(st.session_state.query_history) - i}", key=f"context_q_{i}"):
                if entry.get("retrieved_chunks"):
                    for j, chunk in enumerate(entry["retrieved_chunks"]):
                        st.markdown(f"**Chunk {j+1}:**")
                        st.write(chunk.get("document", "N/A"))
                        if chunk.get("metadata"):
                            st.json(chunk["metadata"])
                        st.markdown("---")
                else:
                    st.info("No relevant chunks retrieved for this query.")
            st.markdown("---")

st.caption(f"Connected to FastAPI backend at: {FASTAPI_URL}")
