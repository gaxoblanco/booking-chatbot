"""
ML Intent Service - FastAPI Main
=================================
Entry point de la aplicación FastAPI.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings, validate_config
from app.models import (
    PredictRequest, PredictResponse,
    BatchPredictRequest, BatchPredictResponse, BatchPrediction,
    HealthResponse, ErrorResponse
)
from app.health import health_checker
from app.security import verify_api_key, verify_ip_whitelist
from ml.ml_intent_detector import ml_intent_detector


# ==========================================
# CONFIGURACIÓN DE LOGGING
# ==========================================
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ==========================================
# LIFESPAN - INICIALIZACIÓN Y CLEANUP
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager.

    Ejecuta código al iniciar y al detener el servicio.
    """
    # ==========================================
    # STARTUP
    # ==========================================
    logger.info("="*60)
    logger.info("🚀 INICIANDO ML INTENT SERVICE")
    logger.info("="*60)

    # Validar configuración
    try:
        validate_config()
    except ValueError as e:
        logger.error(f"❌ Error en configuración: {e}")
        raise

    # Cargar modelo ML
    try:
        logger.info(f"📂 Cargando modelo desde: {settings.model_path}")
        ml_intent_detector.load_model()

        # Obtener info del modelo
        accuracy = getattr(ml_intent_detector, 'accuracy', None)
        intents_count = len(
            ml_intent_detector.intents) if ml_intent_detector.is_loaded else 0

        # Actualizar health checker
        health_checker.set_model_loaded(
            loaded=ml_intent_detector.is_loaded,
            accuracy=accuracy,
            intents_count=intents_count
        )

        if ml_intent_detector.is_loaded:
            logger.info(f"✅ Modelo cargado exitosamente")
            if accuracy:
                logger.info(f"   Accuracy: {accuracy:.1%}")
            logger.info(f"   Intenciones: {intents_count}")
            logger.info(f"   Lista: {ml_intent_detector.intents}")
        else:
            logger.error(f"❌ Modelo no se pudo cargar")
            raise RuntimeError("Failed to load ML model")

    except Exception as e:
        logger.error(f"❌ Error cargando modelo: {e}")
        raise

    logger.info("="*60)
    logger.info(f"✅ Servicio listo en http://{settings.host}:{settings.port}")
    logger.info("="*60)

    yield

    # ==========================================
    # SHUTDOWN
    # ==========================================
    logger.info("🛑 Deteniendo servicio...")
    logger.info("✅ Servicio detenido correctamente")


# ==========================================
# CREAR APLICACIÓN FASTAPI
# ==========================================
app = FastAPI(
    title="ML Intent Service",
    description="Servicio centralizado de detección de intenciones usando spaCy",
    version="1.0.0",
    lifespan=lifespan
)


# ==========================================
# MIDDLEWARE
# ==========================================

# CORS - Configuración de seguridad
app.add_middleware(
    CORSMiddleware,
    # En producción: lista específica de dominios
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


# Middleware de logging de requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log de todas las requests."""
    start_time = time.time()

    # Verificar IP whitelist si está habilitado
    if settings.ip_whitelist_enabled:
        client_ip = request.client.host
        if not verify_ip_whitelist(client_ip):
            return JSONResponse(
                status_code=403,
                content={"error": "IP not authorized"}
            )

    # Procesar request
    response = await call_next(request)

    # Calcular tiempo de procesamiento
    process_time = (time.time() - start_time) * 1000  # ms

    # Log
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.2f}ms"
    )

    return response


# ==========================================
# EXCEPTION HANDLERS
# ==========================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handler para HTTPException."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "detail": None
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handler para excepciones generales."""
    logger.error(f"❌ Error no manejado: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.is_development() else None
        }
    )


# ==========================================
# ENDPOINTS
# ==========================================

@app.get("/", include_in_schema=False)
async def root():
    """
    Root endpoint - Redirige a /docs.
    """
    return {
        "message": "ML Intent Service",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Verifica el estado del servicio y del modelo ML"
)
async def health():
    """
    Health check del servicio.

    Returns:
        Estado del servicio, modelo y métricas de uptime
    """
    status = health_checker.get_status()

    if not status["model_loaded"]:
        raise HTTPException(
            status_code=503,
            detail="Service unavailable: Model not loaded"
        )

    return HealthResponse(**status)


@app.post(
    "/predict",
    response_model=PredictResponse,
    summary="Predecir Intención",
    description="Predice la intención de un mensaje usando el modelo ML. Requiere API Key si está habilitada."
)
async def predict(
    request: PredictRequest,
    api_key: str = Security(verify_api_key)  # ⭐ Autenticación
):
    """
    Predice la intención de un mensaje.

    Args:
        request: PredictRequest con el mensaje

    Returns:
        PredictResponse con intent, confidence y scores

    Example:
        Request:
            POST /predict
            {"message": "necesito psicólogo mañana"}

        Response:
            {
                "intent": "search_professional",
                "confidence": 0.97,
                "ml_scores": {...},
                "processing_time_ms": 15
            }
    """
    # Verificar que el modelo esté cargado
    if not ml_intent_detector.is_loaded:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded"
        )

    # Medir tiempo de procesamiento
    start_time = time.time()

    try:
        # Predecir intención
        result = ml_intent_detector.detect(request.message)

        # Si hubo error en la predicción
        if 'error' in result:
            raise HTTPException(
                status_code=500,
                detail=f"Prediction failed: {result['error']}"
            )

        # Calcular tiempo de procesamiento
        processing_time_ms = (time.time() - start_time) * 1000

        # Log (solo en DEBUG)
        if settings.is_development():
            logger.debug(
                f"Prediction: '{request.message}' → "
                f"{result['intent'].value} ({result['confidence']:.2f})"
            )

        # Retornar respuesta
        return PredictResponse(
            intent=result['intent'].value,
            confidence=result['confidence'],
            ml_scores=result['ml_scores'],
            processing_time_ms=processing_time_ms
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en predicción: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Prediction error: {str(e)}"
        )


@app.post(
    "/predict/batch",
    response_model=BatchPredictResponse,
    summary="Predecir Intenciones (Batch)",
    description="Predice las intenciones de múltiples mensajes en una sola request. Requiere API Key si está habilitada."
)
async def predict_batch(
    request: BatchPredictRequest,
    api_key: str = Security(verify_api_key)  # ⭐ Autenticación
):
    """
    Predice la intención de múltiples mensajes.

    Args:
        request: BatchPredictRequest con lista de mensajes

    Returns:
        BatchPredictResponse con lista de predicciones

    Example:
        Request:
            POST /predict/batch
            {
                "messages": [
                    "necesito psicólogo",
                    "ver mis turnos",
                    "hola"
                ]
            }

        Response:
            {
                "predictions": [
                    {
                        "message": "necesito psicólogo",
                        "intent": "search_professional",
                        "confidence": 0.98
                    },
                    ...
                ],
                "total_processing_time_ms": 42
            }
    """
    # Verificar que el modelo esté cargado
    if not ml_intent_detector.is_loaded:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded"
        )

    # Medir tiempo total
    start_time = time.time()

    try:
        # Procesar cada mensaje
        predictions = []

        for message in request.messages:
            # Predecir
            result = ml_intent_detector.detect(message)

            # Agregar a resultados
            predictions.append(
                BatchPrediction(
                    message=message,
                    intent=result['intent'].value,
                    confidence=result['confidence']
                )
            )

        # Calcular tiempo total
        total_time_ms = (time.time() - start_time) * 1000

        # Log
        logger.info(
            f"Batch prediction: {len(predictions)} messages in {total_time_ms:.2f}ms")

        return BatchPredictResponse(
            predictions=predictions,
            total_processing_time_ms=total_time_ms
        )

    except Exception as e:
        logger.error(f"❌ Error en batch prediction: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Batch prediction error: {str(e)}"
        )


# ==========================================
# MAIN (solo para testing local)
# ==========================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )
