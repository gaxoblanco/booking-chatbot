"""
Health Checks y Métricas
=========================
Monitoreo del estado del servicio.
"""

import time
from typing import Dict
from app.config import settings


class HealthChecker:
    """
    Gestor de health checks y métricas.
    
    Responsabilidades:
    - Verificar estado del servicio
    - Retornar métricas de uptime
    - Verificar modelo ML cargado
    """
    
    def __init__(self):
        """Inicializar health checker."""
        self.start_time = time.time()
        self.model_loaded = False
        self.model_accuracy = None
        self.intents_count = 0
    
    def set_model_loaded(
        self,
        loaded: bool,
        accuracy: float = None,
        intents_count: int = 0
    ):
        """
        Actualiza estado del modelo.
        
        Args:
            loaded: Si el modelo está cargado
            accuracy: Accuracy del modelo (0.0-1.0)
            intents_count: Número de intenciones soportadas
        """
        self.model_loaded = loaded
        self.model_accuracy = accuracy
        self.intents_count = intents_count
    
    def get_uptime(self) -> float:
        """
        Retorna tiempo activo en segundos.
        
        Returns:
            Segundos desde que inició el servicio
        """
        return time.time() - self.start_time
    
    def is_healthy(self) -> bool:
        """
        Verifica si el servicio está saludable.
        
        Returns:
            True si el modelo está cargado
        """
        return self.model_loaded
    
    def get_status(self) -> Dict:
        """
        Retorna estado completo del servicio.
        
        Returns:
            Diccionario con estado y métricas
        """
        return {
            "status": "healthy" if self.is_healthy() else "unhealthy",
            "model_loaded": self.model_loaded,
            "model_accuracy": self.model_accuracy,
            "intents_count": self.intents_count,
            "uptime_seconds": self.get_uptime()
        }


# ==========================================
# INSTANCIA GLOBAL
# ==========================================
health_checker = HealthChecker()
