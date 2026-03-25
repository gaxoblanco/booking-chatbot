"""
Configuración del servicio ML
==============================
Carga variables de entorno y configuración global.
"""

from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    """
    Configuración del servicio.
    
    Carga valores desde variables de entorno o usa defaults.
    """
    
    # ==========================================
    # MODELO ML
    # ==========================================
    model_path: str = "models/intent_classifier"
    """Ruta al modelo spaCy entrenado"""
    
    # ==========================================
    # SERVIDOR
    # ==========================================
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    reload: bool = False
    """Hot reload para desarrollo"""
    
    # ==========================================
    # LOGGING
    # ==========================================
    log_level: str = "INFO"
    """DEBUG, INFO, WARNING, ERROR, CRITICAL"""
    
    # ==========================================
    # SEGURIDAD
    # ==========================================
    api_key_enabled: bool = False
    """Si True, requiere X-API-Key header en requests"""
    
    api_key: Optional[str] = None
    """API key válida (generar con: python app/security.py)"""
    
    # IP Whitelist
    ip_whitelist_enabled: bool = False
    """Si True, solo permite IPs en la whitelist"""
    
    ip_whitelist: list = []
    """Lista de IPs permitidas (ejemplo: ['172.18.0.0/16', '10.0.0.0/8'])"""
    
    # Rate Limiting
    rate_limit_enabled: bool = False
    """Si True, aplica rate limiting"""
    
    rate_limit_requests: int = 100
    """Máximo de requests por ventana"""
    
    rate_limit_window: int = 60
    """Ventana de tiempo en segundos"""
    
    # CORS
    cors_origins: list = ["*"]
    """Lista de orígenes permitidos para CORS. En producción usar lista específica"""
    
    cors_allow_credentials: bool = True
    cors_allow_methods: list = ["GET", "POST"]
    cors_allow_headers: list = ["*"]
    
    # ==========================================
    # CACHE (FUTURO)
    # ==========================================
    cache_enabled: bool = False
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    cache_ttl_seconds: int = 3600
    
    # ==========================================
    # MÉTRICAS (FUTURO)
    # ==========================================
    metrics_enabled: bool = False
    metrics_port: int = 9090
    
    # ==========================================
    # TIMEZONE
    # ==========================================
    tz: str = "America/Argentina/Buenos_Aires"
    
    class Config:
        """Configuración de pydantic."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def get_model_path(self) -> Path:
        """
        Retorna Path object del modelo.
        
        Returns:
            Path al directorio del modelo
        """
        return Path(self.model_path)
    
    def is_development(self) -> bool:
        """
        Verifica si está en modo desarrollo.
        
        Returns:
            True si log_level es DEBUG
        """
        return self.log_level.upper() == "DEBUG"


# ==========================================
# INSTANCIA GLOBAL
# ==========================================
settings = Settings()


# ==========================================
# VALIDACIÓN AL INICIAR
# ==========================================
def validate_config():
    """
    Valida que la configuración sea correcta.
    
    Raises:
        ValueError: Si la configuración es inválida
    """
    # Validar que existe el modelo
    model_path = settings.get_model_path()
    if not model_path.exists():
        raise ValueError(
            f"Modelo no encontrado en: {model_path}\n"
            f"Asegúrate de entrenar el modelo primero con:\n"
            f"  cd scripts\n"
            f"  python generate_training_dataset.py\n"
            f"  python train_spacy_model.py --data ../dataset/dataset_training.jsonl"
        )
    
    # Validar archivos críticos del modelo
    critical_files = ["config.cfg", "meta.json"]
    for filename in critical_files:
        if not (model_path / filename).exists():
            raise ValueError(
                f"Archivo crítico no encontrado: {model_path / filename}\n"
                f"El modelo parece estar incompleto o corrupto."
            )
    
    # Validar log level
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if settings.log_level.upper() not in valid_levels:
        raise ValueError(
            f"LOG_LEVEL inválido: {settings.log_level}\n"
            f"Valores válidos: {valid_levels}"
        )
    
    # Validar workers
    if settings.workers < 1:
        raise ValueError("WORKERS debe ser >= 1")
    
    print(f"✅ Configuración validada correctamente")
    print(f"   Modelo: {settings.model_path}")
    print(f"   Log level: {settings.log_level}")
    print(f"   Workers: {settings.workers}")
