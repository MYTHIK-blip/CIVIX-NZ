import streamlit as st
import httpx
import os

# Configuration for the FastAPI backend
FASTAPI_HOST = os.getenv("FASTAPI_HOST", "http://localhost")
FASTAPI_PORT = os.getenv("FASTAPI_PORT", "8000")
FASTAPI_URL = f"{FASTAPI_HOST}:{FASTAPI_PORT}"

st.set_page_config(page_title="ComplianceRAG UI", layout="wide")

st.title("ComplianceRAG: Ask Your Documents")

# User input for the query
query_text = st.text_area("Enter your question here:", height=100)
top_k = st.slider("Number of relevant chunks to retrieve:", min_value=1, max_value=10, value=3)

if st.button("Get Answer"):
    if query_text:
        with st.spinner("Searching and generating answer..."):
            try:
                response = httpx.post(
                    f"{FASTAPI_URL}/query",
                    json={"query_text": query_text, "top_k": top_k},
                    timeout=300.0 # Increased timeout for potentially long generation
                )
                response.raise_for_status() # Raise an exception for 4xx or 5xx status codes
                result = response.json()

                st.subheader("Generated Answer:")
                st.write(result.get("answer", "No answer generated."))

                st.subheader("Retrieved Context:")
                if result.get("retrieved_chunks"):
                    for i, chunk in enumerate(result["retrieved_chunks"]):
                        st.markdown(f"**Chunk {i+1}:**")
                        st.write(chunk.get("text", "N/A"))
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
st.caption(f"Connected to FastAPI backend at: {FASTAPI_URL}")
