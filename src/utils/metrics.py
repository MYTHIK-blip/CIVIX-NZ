from prometheus_client import Counter, Histogram, Gauge

# Define Prometheus metrics
# Counters for request counts
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP Requests',
    ['method', 'endpoint', 'status_code']
)

# Histograms for request durations
REQUEST_LATENCY_SECONDS = Histogram(
    'http_request_duration_seconds',
    'HTTP Request Duration in seconds',
    ['method', 'endpoint']
)

# Gauge for in-progress requests
IN_PROGRESS_REQUESTS = Gauge(
    'http_requests_in_progress',
    'Number of in-progress HTTP requests',
    ['method', 'endpoint']
)

# Custom metrics for RAG pipeline components
INGESTION_DURATION_SECONDS = Histogram(
    'ingestion_duration_seconds',
    'Duration of document ingestion in seconds',
    ['doc_id', 'status']
)

RETRIEVAL_DURATION_SECONDS = Histogram(
    'retrieval_duration_seconds',
    'Duration of document retrieval in seconds',
    ['query_text_hash'] # Use hash to avoid high cardinality
)

RERANKING_DURATION_SECONDS = Histogram(
    'reranking_duration_seconds',
    'Duration of re-ranking in seconds',
    ['query_text_hash']
)

GENERATION_DURATION_SECONDS = Histogram(
    'generation_duration_seconds',
    'Duration of answer generation in seconds',
    ['model_name']
)

EMBEDDING_DURATION_SECONDS = Histogram(
    'embedding_duration_seconds',
    'Duration of text embedding in seconds',
    ['model_name', 'batch_size']
)

CHROMA_QUERY_DURATION_SECONDS = Histogram(
    'chroma_query_duration_seconds',
    'Duration of ChromaDB query operations in seconds'
)

OLLAMA_API_CALL_DURATION_SECONDS = Histogram(
    'ollama_api_call_duration_seconds',
    'Duration of Ollama API calls in seconds',
    ['model_name']
)
