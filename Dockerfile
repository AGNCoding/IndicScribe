# Use official Python lightweight image
FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND noninteractive

# Install system dependencies
# poppler-utils is required by pdf2image
# ffmpeg is recommended for pydub to handle various audio formats
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY static/ ./static/

# The application expects GOOGLE_APPLICATION_CREDENTIALS to point to a json file.
# This should be mounted as a volume or provided via secret in production.
# Example: -v /path/to/creds.json:/app/credentials/google_credentials.json

# Expose port
EXPOSE 8000

# Run the application with uvicorn
# In production, increasing workers is recommended: --workers 4
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
