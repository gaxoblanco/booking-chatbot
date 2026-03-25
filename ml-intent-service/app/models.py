"""
Pydantic Models para Request/Response
======================================
Define schemas de validación para la API.
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional


class PredictRequest(BaseModel):
    """
    Request para predicción de intención.
    
    Example:
        {
            "message": "necesito psicólogo mañana"
        }
    """
    message: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Mensaje del usuario para clasificar"
    )
    
    @validator('message')
    def validate_message(cls, v):
        """Valida que el mensaje no esté vacío."""
        if not v or not v.strip():
            raise ValueError("El mensaje no puede estar vacío")
        return v.strip()


class PredictResponse(BaseModel):
    """
    Response de predicción de intención.
    
    Example:
        {
            "intent": "search_professional",
            "confidence": 0.97,
            "ml_scores": {
                "search_professional": 0.97,
                "view_my_appointments": 0.01,
                ...
            },
            "processing_time_ms": 15
        }
    """
    intent: str = Field(
        ...,
        description="Intención detectada"
    )
    
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confianza de la predicción (0.0-1.0)"
    )
    
    ml_scores: Dict[str, float] = Field(
        ...,
        description="Scores de todas las intenciones"
    )
    
    processing_time_ms: float = Field(
        ...,
        description="Tiempo de procesamiento en milisegundos"
    )


class BatchPredictRequest(BaseModel):
    """
    Request para predicción batch.
    
    Example:
        {
            "messages": [
                "necesito psicólogo",
                "ver mis turnos",
                "hola"
            ]
        }
    """
    messages: List[str] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="Lista de mensajes para clasificar (máximo 100)"
    )
    
    @validator('messages')
    def validate_messages(cls, v):
        """Valida que todos los mensajes sean válidos."""
        cleaned = []
        for msg in v:
            if not msg or not msg.strip():
                continue  # Ignorar mensajes vacíos
            cleaned.append(msg.strip())
        
        if not cleaned:
            raise ValueError("Debe haber al menos un mensaje válido")
        
        return cleaned


class BatchPrediction(BaseModel):
    """
    Predicción individual dentro de un batch.
    
    Example:
        {
            "message": "necesito psicólogo",
            "intent": "search_professional",
            "confidence": 0.98
        }
    """
    message: str = Field(..., description="Mensaje original")
    intent: str = Field(..., description="Intención detectada")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confianza")


class BatchPredictResponse(BaseModel):
    """
    Response de predicción batch.
    
    Example:
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
    predictions: List[BatchPrediction] = Field(
        ...,
        description="Lista de predicciones"
    )
    
    total_processing_time_ms: float = Field(
        ...,
        description="Tiempo total de procesamiento en milisegundos"
    )


class HealthResponse(BaseModel):
    """
    Response de health check.
    
    Example:
        {
            "status": "healthy",
            "model_loaded": true,
            "model_accuracy": 0.981,
            "intents_count": 7,
            "uptime_seconds": 3600
        }
    """
    status: str = Field(..., description="Estado del servicio")
    model_loaded: bool = Field(..., description="Si el modelo está cargado")
    model_accuracy: Optional[float] = Field(None, description="Accuracy del modelo")
    intents_count: int = Field(..., description="Número de intenciones soportadas")
    uptime_seconds: float = Field(..., description="Tiempo activo en segundos")


class ErrorResponse(BaseModel):
    """
    Response de error.
    
    Example:
        {
            "error": "Model not loaded",
            "detail": "spaCy model failed to load from models/intent_classifier"
        }
    """
    error: str = Field(..., description="Mensaje de error")
    detail: Optional[str] = Field(None, description="Detalles adicionales del error")
