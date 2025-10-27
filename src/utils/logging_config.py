import logging
from pythonjsonlogger import jsonlogger
import sys

def setup_logging():
    """
    Sets up structured JSON logging for the application.
    """
    log_handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s'
    )
    log_handler.setFormatter(formatter)

    # Get the root logger and add the handler
    root_logger = logging.getLogger()
    root_logger.addHandler(log_handler)
    root_logger.setLevel(logging.INFO) # Default level

    # Prevent duplicate logs if other handlers are already configured
    root_logger.propagate = False

    # Configure uvicorn's access logger to use our structured format
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.addHandler(log_handler)
    uvicorn_access_logger.setLevel(logging.INFO)
    uvicorn_access_logger.propagate = False

    # Configure uvicorn's default logger to use our structured format
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.addHandler(log_handler)
    uvicorn_logger.setLevel(logging.INFO)
    uvicorn_logger.propagate = False

    logging.info("Structured logging configured.")

if __name__ == "__main__":
    setup_logging()
    logging.info("Test structured log message.", extra={"key": "value", "user_id": 123})
    logging.warning("This is a warning.")
    logging.error("This is an error.", exc_info=True)
