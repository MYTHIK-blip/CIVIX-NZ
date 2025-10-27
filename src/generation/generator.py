

import os
import logging
import httpx
from typing import List, Dict, Any

# Logging is configured globally by src.utils.logging_config
# No need for logging.basicConfig here.

# --- Constants and Configuration ---
OLLAMA_API_BASE_URL = os.getenv("OLLAMA_API_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral") # User specified mistral instruct

# --- Generation Function ---

def generate_answer(query: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
    """
    Generates an answer using an LLM based on the query and retrieved context.

    Args:
        query: The user's original query.
        retrieved_chunks: A list of dictionaries, each representing a retrieved document chunk.

    Returns:
        A string containing the generated answer.
    """
    if not retrieved_chunks:
        return "I couldn't find any relevant information to answer your question."

    context = "\n\n".join([chunk["document"] for chunk in retrieved_chunks])

    # Construct the prompt for the LLM
    # This prompt structure is a common pattern for RAG with instruction-tuned models.
    prompt = f"""Using the following context, answer the question at the end. 
If you don't know the answer, just say that you don't know, don't try to make up an answer.

Context:
{context}

Question: {query}
Answer:"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False # We want the full response at once
    }

    headers = {"Content-Type": "application/json"}

    try:
        logging.info(f"Sending request to Ollama API for model: {OLLAMA_MODEL}")
        response = httpx.post(f"{OLLAMA_API_BASE_URL}/api/generate", json=payload, headers=headers, timeout=300.0)
        response.raise_for_status() # Raise an exception for 4xx or 5xx status codes
        
        response_data = response.json()
        generated_text = response_data.get("response", "").strip()

        if not generated_text:
            logging.warning("Ollama API returned an empty response.")
            return "I received an empty response from the language model."

        return generated_text

    except httpx.RequestError as e:
        logging.error(f"An error occurred while requesting {e.request.url!r}: {e}", exc_info=True)
        return f"Failed to connect to the language model. Please ensure Ollama is running at {OLLAMA_API_BASE_URL}."
    except httpx.HTTPStatusError as e:
        logging.error(f"Error response {e.response.status_code} while requesting {e.request.url!r}: {e}", exc_info=True)
        return f"Language model returned an error: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        logging.error(f"An unexpected error occurred during text generation: {e}", exc_info=True)
        return "An unexpected error occurred while generating the answer."

