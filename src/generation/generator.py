

import os
import logging
import httpx
import time
from typing import List, Dict, Any

from src.utils.tracing import tracer
from src.utils.metrics import GENERATION_DURATION_SECONDS, OLLAMA_API_CALL_DURATION_SECONDS

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
    start_time = time.time()
    with tracer.start_as_current_span("generate_answer") as span:
        span.set_attribute("generation.query", query)
        span.set_attribute("generation.retrieved_chunks_count", len(retrieved_chunks))
        span.set_attribute("generation.model_name", OLLAMA_MODEL)

        if not retrieved_chunks:
            span.set_attribute("generation.status", "no_relevant_chunks")
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
            ollama_call_start_time = time.time()
            with tracer.start_as_current_span("ollama_api_call") as ollama_span:
                ollama_span.set_attribute("ollama.model", OLLAMA_MODEL)
                logging.info(f"Sending request to Ollama API for model: {OLLAMA_MODEL}", extra={"ollama_model": OLLAMA_MODEL})
                response = httpx.post(f"{OLLAMA_API_BASE_URL}/api/generate", json=payload, headers=headers, timeout=300.0)
                response.raise_for_status() # Raise an exception for 4xx or 5xx status codes
                
                response_data = response.json()
                generated_text = response_data.get("response", "").strip()

                ollama_call_duration = time.time() - ollama_call_start_time
                OLLAMA_API_CALL_DURATION_SECONDS.labels(model_name=OLLAMA_MODEL).observe(ollama_call_duration)
                ollama_span.set_attribute("ollama.duration_seconds", ollama_call_duration)

            if not generated_text:
                logging.warning("Ollama API returned an empty response.", extra={"ollama_model": OLLAMA_MODEL})
                span.set_attribute("generation.status", "empty_response")
                return "I received an empty response from the language model."

            span.set_attribute("generation.status", "success")
            return generated_text

        except httpx.RequestError as e:
            logging.error(f"An error occurred while requesting {e.request.url!r}: {e}", exc_info=True, extra={"ollama_url": e.request.url})
            span.set_attribute("generation.status", "network_error")
            return f"Failed to connect to the language model. Please ensure Ollama is running at {OLLAMA_API_BASE_URL}."
        except httpx.HTTPStatusError as e:
            logging.error(f"Error response {e.response.status_code} while requesting {e.request.url!r}: {e}", exc_info=True, extra={"ollama_url": e.request.url, "status_code": e.response.status_code})
            span.set_attribute("generation.status", "http_error")
            return f"Language model returned an error: {e.response.status_code} - {e.response.text}"
        except Exception as e:
            logging.error(f"An unexpected error occurred during text generation: {e}", exc_info=True)
            span.set_attribute("generation.status", "unexpected_error")
            return "An unexpected error occurred while generating the answer."
        finally:
            generation_duration = time.time() - start_time
            GENERATION_DURATION_SECONDS.labels(model_name=OLLAMA_MODEL).observe(generation_duration)
            span.set_attribute("generation.duration_seconds", generation_duration)

