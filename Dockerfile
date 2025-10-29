# Use an official Python runtime as a parent image
FROM python:3.12-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for pypdf and docx
# This includes build-essential for compiling some Python packages
# and libgl1-mesa-glx for potential headless rendering (though not strictly for pypdf/docx)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1-mesa-glx \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the current working directory into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
# Use --no-cache-dir to avoid caching pip packages, reducing image size
# Use --break-system-packages to allow pip to install packages in a virtual environment
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Download the spaCy English model
RUN python -m spacy download en_core_web_sm

# Expose the port that the FastAPI application listens on
EXPOSE 8000

# Define environment variables for the application
ENV EMBED_MODEL=./models/all-MiniLM-L6-v2
ENV CHROMA_DIR=./data/chroma
ENV INGESTION_MANIFEST_PATH=./data/ingestion_manifest.json

# Run the FastAPI application using Uvicorn
# --host 0.0.0.0 makes the server accessible from outside the container
CMD ["uvicorn", "ingestion_service:app", "--host", "0.0.0.0", "--port", "8000"]
