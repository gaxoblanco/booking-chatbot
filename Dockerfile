# ==================================================
# WHATSAPP BOT WEBHOOK - DOCKERFILE
# ==================================================
# Multi-stage build for optimized image size
# Python 3.10 slim base image

# ==================================================
# STAGE 1: BASE IMAGE
# ==================================================
FROM python:3.10-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies (if needed in future)
# RUN apt-get update && apt-get install -y \
#     gcc \
#     && rm -rf /var/lib/apt/lists/*

# ==================================================
# STAGE 2: DEPENDENCIES
# ==================================================
FROM base as dependencies

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
FROM dependencies as application

# Copy application files
COPY config.py .
COPY whatsapp_handler.py .
COPY bot.py .
COPY states.py .
COPY messages.py .
COPY validators.py .
COPY database.py .
COPY init_db.py .
COPY domain_config.py .
COPY setup_domain.py .
COPY client_service.py .
COPY professional_service.py .
COPY analytics_service.py .
COPY messaging_utils.py .

COPY docker-setup.sh .
RUN chmod +x docker-setup.sh

# Create directory for certificates (mounted volume in production)
RUN mkdir -p certificates

# Set environment variables
# Python: Don't write .pyc files, unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=whatsapp_handler.py

# Copy application files
COPY *.py /app/
COPY *.sh /app/

# ⭐ AGREGAR: Hacer script ejecutable
RUN chmod +x /app/init_and_run.sh

# Create directories
RUN mkdir -p /app/data /app/certificates

# Expose port
EXPOSE 5000

# ⭐ CAMBIAR CMD:
CMD ["/app/init_and_run.sh"]


# ==================================================
# HEALTH CHECK
# ==================================================
# Check if Flask server is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/', timeout=2)"

# ==================================================
# STARTUP COMMAND
# ==================================================
# Development mode: Flask development server
# Production mode: Use gunicorn (uncomment below)

# Development
# CMD ["python", "whatsapp_handler.py"]
CMD ["bash", "docker-setup.sh"]

# Production (uncomment for production use)
# CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "whatsapp_handler:app"]