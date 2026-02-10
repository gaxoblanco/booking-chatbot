# ==================================================
# WHATSAPP BOT WEBHOOK - DOCKERFILE (OPTIMIZADO)
# ==================================================
# Multi-stage build optimizado para desarrollo rápido
# Python 3.10 slim base image

# ==================================================
# STAGE 1: SYSTEM BASE (Cacheable - rara vez cambia)
# ==================================================
FROM python:3.10-slim AS system-base

# Install system dependencies
# curl: for healthcheck
# bash: for entrypoint script
RUN apt-get update && apt-get install -y \
    curl \
    bash \
    && rm -rf /var/lib/apt/lists/*

# ==================================================
# STAGE 2: PYTHON DEPENDENCIES (Cacheable - cambia poco)
# ==================================================
FROM system-base AS python-deps

WORKDIR /app

# Copy ONLY requirements first (mejor cache)
COPY requirements.txt .

# Install Python dependencies + spaCy model
# Descarga directa del .whl (más confiable que spacy download)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install https://github.com/explosion/spacy-models/releases/download/es_core_news_sm-3.7.0/es_core_news_sm-3.7.0-py3-none-any.whl

# ==================================================
# STAGE 3: APPLICATION (Cambia frecuentemente)
# ==================================================
FROM python-deps AS application

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    FLASK_APP=src.api.whatsapp_handler

# Create necessary directories ANTES de copiar archivos
RUN mkdir -p /app/data/certificates && \
    mkdir -p /app/data && \
    mkdir -p /app/data/conversations && \
    mkdir -p /app/dataset && \
    mkdir -p /app/src/integrations/google_calendar_service/config/google && \
    mkdir -p /app/scripts/ml/models

# Copy application files (estos cambian frecuentemente)
COPY src/ /app/src/
COPY scripts/ /app/scripts/
COPY .env.example /app/

# Copy Docker entrypoint script
COPY docker/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Expose port
EXPOSE 5000

# ==================================================
# HEALTH CHECK
# ==================================================
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# ==================================================
# STARTUP COMMAND
# ==================================================
# Development (default)
CMD ["/app/docker-entrypoint.sh"]

# Production (use gunicorn)
# CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "src.api.whatsapp_handler:app"]

# ==================================================
# BUILD INSTRUCTIONS
# ==================================================
# Fast rebuild (usa cache):
#   docker-compose build
#
# Clean rebuild (sin cache):
#   docker-compose build --no-cache
#
# Rebuild solo dependencies (si cambió requirements.txt):
#   docker-compose build --no-cache python-deps
#   docker-compose build