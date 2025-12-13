# ==================================================
# WHATSAPP BOT WEBHOOK - DOCKERFILE
# ==================================================
# Multi-stage build for optimized image size
# Python 3.10 slim base image

# ==================================================
# STAGE 1: BASE IMAGE
# ==================================================
FROM python:3.10-slim AS base

# Set working directory
WORKDIR /app

# Install system dependencies
# curl: for healthcheck
# bash: for entrypoint script
RUN apt-get update && apt-get install -y \
    curl \
    bash \
    && rm -rf /var/lib/apt/lists/*

# ==================================================
# STAGE 2: DEPENDENCIES
# ==================================================
FROM base AS dependencies

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir: Don't cache pip packages (smaller image)
# --upgrade: Ensure latest compatible versions
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ==================================================
# STAGE 3: APPLICATION
# ==================================================
FROM dependencies AS application

# Set working directory
WORKDIR /app

# Copy application files (desde el contexto raíz)
COPY src/ /app/src/
COPY scripts/ /app/scripts/
COPY .env.example /app/

# Copy Docker entrypoint script (desde el contexto raíz)
COPY docker/docker-entrypoint.sh /app/docker-entrypoint.sh

# Make entrypoint executable
RUN chmod +x /app/docker-entrypoint.sh

# Create necessary directories
RUN mkdir -p /app/data/certificates && \
    mkdir -p /app/data

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    FLASK_APP=src.api.whatsapp_handler

# Expose port
EXPOSE 5000

# ==================================================
# HEALTH CHECK
# ==================================================
# Check if Flask server is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# ==================================================
# STARTUP COMMAND
# ==================================================
# Development mode: Uses docker-entrypoint.sh for setup + Flask dev server
# Production mode: Use gunicorn (uncomment below)

# Development (default)
CMD ["/app/docker-entrypoint.sh"]

# Production (uncomment for production use)
# CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "src.api.whatsapp_handler:app"]