"""
Security - Autenticación y Autorización
========================================
Implementa autenticación por API Key para producción.
"""

import logging
import secrets
from typing import Optional
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from app.config import settings


logger = logging.getLogger(__name__)


# ==========================================
# API KEY AUTHENTICATION
# ==========================================

# Header donde se espera la API key
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    Verifica que la API key sea válida.
    
    Args:
        api_key: API key del header
    
    Returns:
        API key válida
    
    Raises:
        HTTPException: Si la key es inválida o falta
    """
    # Si autenticación está deshabilitada, permitir acceso
    if not settings.api_key_enabled:
        return "disabled"
    
    # Verificar que se proporcionó una key
    if not api_key:
        logger.warning("❌ Request sin API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Verificar que la key sea correcta
    if not secrets.compare_digest(api_key, settings.api_key):
        logger.warning(f"❌ API key inválida: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Key válida
    logger.debug("✅ API key válida")
    return api_key


# ==========================================
# IP WHITELIST (OPCIONAL)
# ==========================================

def verify_ip_whitelist(client_ip: str) -> bool:
    """
    Verifica que la IP esté en la whitelist.
    
    Args:
        client_ip: IP del cliente
    
    Returns:
        True si la IP está permitida
    """
    # Si whitelist está deshabilitada, permitir todas
    if not settings.ip_whitelist_enabled:
        return True
    
    # Verificar contra whitelist
    allowed = client_ip in settings.ip_whitelist
    
    if not allowed:
        logger.warning(f"❌ IP no autorizada: {client_ip}")
    
    return allowed


# ==========================================
# RATE LIMITING (FUTURO)
# ==========================================

class RateLimiter:
    """
    Rate limiter simple en memoria.
    
    Para producción real, usar Redis.
    """
    
    def __init__(self):
        """Inicializar rate limiter."""
        self.requests = {}  # {api_key: [(timestamp, count)]}
    
    def check_rate_limit(self, api_key: str, limit: int = 100, window: int = 60) -> bool:
        """
        Verifica rate limit.
        
        Args:
            api_key: API key del cliente
            limit: Máximo de requests en la ventana
            window: Ventana de tiempo en segundos
        
        Returns:
            True si está dentro del límite
        """
        # TODO: Implementar rate limiting real
        # Por ahora, siempre permitir
        return True


# Instancia global
rate_limiter = RateLimiter()


# ==========================================
# HELPERS
# ==========================================

def generate_api_key() -> str:
    """
    Genera una API key segura.
    
    Returns:
        API key de 32 caracteres hexadecimales
    
    Example:
        >>> key = generate_api_key()
        >>> print(key)
        'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6'
    """
    return secrets.token_hex(32)


def hash_api_key(api_key: str) -> str:
    """
    Hashea una API key para logging seguro.
    
    Args:
        api_key: API key a hashear
    
    Returns:
        Primeros 8 caracteres + ...
    
    Example:
        >>> hash_api_key("a1b2c3d4e5f6...")
        'a1b2c3d4...'
    """
    return f"{api_key[:8]}..." if len(api_key) > 8 else api_key


# ==========================================
# SCRIPT DE GENERACIÓN DE KEY (main)
# ==========================================

if __name__ == "__main__":
    print("="*60)
    print("🔑 GENERADOR DE API KEYS")
    print("="*60)
    print("\nGenerando nueva API key segura...\n")
    
    key = generate_api_key()
    
    print(f"API Key generada:\n")
    print(f"  {key}\n")
    print("Agrega esta key a tu .env:\n")
    print(f"  API_KEY_ENABLED=true")
    print(f"  API_KEY={key}\n")
    print("Y compártela solo con servicios autorizados.")
    print("="*60)
