FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_ENV=production \
    PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install gunicorn

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs DATA Classes/chroma_db

# Expose port
EXPOSE 5895

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5895/health')"

# Run with gunicorn in production
CMD ["gunicorn", "--bind", "0.0.0.0:5895", "--workers", "2", "--threads", "2", "--worker-class", "gthread", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
