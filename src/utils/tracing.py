import os
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
import logging

# Configure logging for this module
logger = logging.getLogger(__name__)

def setup_tracing(app=None, service_name="compliance-rag-api"):
    """
    Sets up OpenTelemetry tracing for the application.
    """
    # Resource can be anything that identifies your service.
    resource = Resource.create({
        "service.name": service_name,
        "service.instance.id": os.getenv("HOSTNAME", "unknown")
    })

    # Set the TracerProvider
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    # Configure OTLP exporter to send traces to a collector (e.g., Jaeger, Tempo)
    # Default endpoint is http://localhost:4317 for gRPC
    otlp_exporter = OTLPSpanExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
        insecure=True # Use insecure for local development without TLS
    )

    # Add a BatchSpanProcessor to the TracerProvider
    span_processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(span_processor)

    # Instrument FastAPI if an app instance is provided
    if app:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumentation enabled.")
    
    # Instrument httpx for outgoing HTTP requests
    HTTPXClientInstrumentor().instrument()
    logger.info("HTTPX client instrumentation enabled.")

    logger.info(f"OpenTelemetry tracing configured for service: {service_name}")
    logger.info(f"OTLP exporter endpoint: {os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://localhost:4317')}")

# Get a tracer for manual instrumentation
tracer = trace.get_tracer(__name__)

if __name__ == "__main__":
    # Example usage for manual testing
    setup_tracing(service_name="test-service")
    with tracer.start_as_current_span("test-span"):
        logger.info("Inside a test span.")
    logger.info("Tracing setup complete for test service.")
