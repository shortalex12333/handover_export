# Dockerfile for Handover Export Service
FROM python:3.11-slim

WORKDIR /app

# System dependencies for WeasyPrint (PDF generation)
RUN apt-get update && apt-get install -y \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    shared-mime-info \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY src/ ./src/
COPY templates/ ./templates/

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/health || exit 1

# Expose port
EXPOSE 10000

# Run application
CMD ["/bin/sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
