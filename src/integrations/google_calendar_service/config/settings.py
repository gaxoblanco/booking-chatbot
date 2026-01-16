"""
Configuración del servicio de Google Calendar.

Define constantes y parámetros configurables para la integración
con Google Calendar API.
"""

import os
from pathlib import Path

# Directorio base del módulo
BASE_DIR = Path(__file__).resolve().parent.parent

# Configuración de Google API
GOOGLE_CONFIG = {
    # Ruta al archivo de credenciales de Service Account
    # Se puede sobrescribir con variable de entorno
    'credentials_path': os.getenv(
        'GOOGLE_CREDENTIALS_PATH',
        str(BASE_DIR / 'config' / 'google' / 'service-account.json')
    ),
    
    # Scopes (permisos) necesarios para operar con calendarios
    'scopes': [
        'https://www.googleapis.com/auth/calendar',           # Acceso completo a calendarios
        'https://www.googleapis.com/auth/calendar.events'     # Gestión de eventos
    ],
    
    # Versión de la API
    'api_version': 'v3',
    
    # Configuración de reintentos para llamadas a la API
    'retry_attempts': 3,        # Número de reintentos en caso de fallo
    'retry_delay_seconds': 2,   # Segundos entre reintentos
    'timeout_seconds': 30,      # Timeout para requests
}

# Zona horaria por defecto
# Puede ser sobrescrita por configuración del profesional
DEFAULT_TIMEZONE = os.getenv('DEFAULT_TIMEZONE', 'America/Argentina/Buenos_Aires')

# Configuración de logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
