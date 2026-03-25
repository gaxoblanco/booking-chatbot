# Dockerfile para ML Intent Service
# Python 3.11 slim para reducir tamaño de imagen

FROM python:3.11-slim

# Metadata
LABEL maintainer="tu-email@ejemplo.com"
LABEL description="ML Intent Detection Service con spaCy"
LABEL version="1.0.0"

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Crear usuario no-root por seguridad
RUN useradd -m -u 1000 mluser && \
    mkdir -p /app && \
    chown -R mluser:mluser /app

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para spaCy
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copiar requirements primero (para aprovechar cache de Docker)
COPY --chown=mluser:mluser requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

RUN python -m spacy download es_core_news_sm || \
    pip install https://github.com/explosion/spacy-models/releases/download/es_core_news_sm-3.7.0/es_core_news_sm-3.7.0-py3-none-any.whl

# Copiar código de la aplicación
COPY --chown=mluser:mluser app/ ./app/
COPY --chown=mluser:mluser ml/ ./ml/

# Copiar modelo entrenado
# IMPORTANTE: El modelo debe existir en models/intent_classifier/
COPY --chown=mluser:mluser models/ ./models/

# Copiar scripts de entrenamiento (opcional, para re-entrenamiento)
RUN mkdir -p /app/models/intent_classifier && \
    chown -R mluser:mluser /app/models

# Cambiar a usuario no-root
USER mluser

# Exponer puerto 8000
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando de inicio
# Usar uvicorn con workers según CPU disponible
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
