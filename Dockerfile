# Dockerfile for Chip - FastAPI + Temporal Worker
# Railway will use this for deployment

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Railway will set PORT env var)
# Use PORT from environment variable (Railway provides this)
EXPOSE ${PORT:-8000}

# Default command: Run FastAPI server
# Railway provides $PORT environment variable automatically
# Temporal worker starts automatically in background via server/app.py startup
CMD sh -c "hypercorn main:app -b 0.0.0.0:${PORT:-8000}"

