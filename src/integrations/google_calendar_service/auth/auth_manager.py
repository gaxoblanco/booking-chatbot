"""
AuthManager - Gestión de autenticación con Google Calendar API.

Este módulo maneja la autenticación usando Service Account de Google Cloud.
Service Account permite que la aplicación acceda a calendarios sin intervención
del usuario, siempre que los calendarios hayan sido compartidos con la cuenta de servicio.

Flujo de autenticación:
1. Cargar credenciales desde archivo JSON
2. Crear objeto de credenciales con los scopes necesarios
3. Las credenciales se pueden usar directamente con el cliente de Google API
"""

import json
import logging
from pathlib import Path
from typing import Optional

from google.oauth2 import service_account
from google.auth.transport.requests import Request

from ..config import GOOGLE_CONFIG

# Configurar logger
logger = logging.getLogger(__name__)


class AuthManager:
    """
    Gestor de autenticación para Google Calendar API.
    
    Maneja la carga de credenciales de Service Account y la generación
    de tokens de acceso para interactuar con la API.
    
    Attributes:
        credentials_path (Path): Ruta al archivo de credenciales JSON
        scopes (list): Lista de permisos (scopes) de Google API
        credentials: Objeto de credenciales de Google (una vez autenticado)
    """
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Inicializa el gestor de autenticación.
        
        Args:
            credentials_path: Ruta al archivo JSON de Service Account.
                            Si no se proporciona, usa la configuración por defecto.
        
        Raises:
            FileNotFoundError: Si el archivo de credenciales no existe
            ValueError: Si el archivo de credenciales es inválido
        """
        # Usar ruta proporcionada o la configurada por defecto
        self.credentials_path = Path(credentials_path or GOOGLE_CONFIG['credentials_path'])
        self.scopes = GOOGLE_CONFIG['scopes']
        self.credentials = None
        
        logger.info(f"AuthManager inicializado con credenciales en: {self.credentials_path}")
        
        # Validar que el archivo existe
        if not self.credentials_path.exists():
            error_msg = f"Archivo de credenciales no encontrado: {self.credentials_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
    
    def get_credentials(self):
        """
        Obtiene las credenciales autenticadas para usar con Google API.
        
        Este método carga las credenciales desde el archivo JSON y las prepara
        para ser usadas con el cliente de Google Calendar API.
        
        Returns:
            google.oauth2.service_account.Credentials: Objeto de credenciales autenticado
        
        Raises:
            ValueError: Si las credenciales son inválidas
            Exception: Si hay un error al procesar las credenciales
        """
        try:
            # Cargar credenciales desde archivo JSON
            logger.info("Cargando credenciales de Service Account...")
            
            self.credentials = service_account.Credentials.from_service_account_file(
                str(self.credentials_path),
                scopes=self.scopes
            )
            
            logger.info("Credenciales cargadas exitosamente")
            logger.debug(f"Service Account email: {self.credentials.service_account_email}")
            
            return self.credentials
            
        except json.JSONDecodeError as e:
            error_msg = f"El archivo de credenciales no es un JSON válido: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        except Exception as e:
            error_msg = f"Error al cargar credenciales: {e}"
            logger.error(error_msg)
            raise
    
    def validate_credentials(self) -> bool:
        """
        Valida que las credenciales sean correctas y tengan los permisos necesarios.
        
        Intenta refrescar el token de acceso para verificar que las credenciales
        funcionen correctamente.
        
        Returns:
            bool: True si las credenciales son válidas, False en caso contrario
        """
        try:
            if self.credentials is None:
                self.get_credentials()
            
            # Intentar refrescar el token para validar
            logger.info("Validando credenciales...")
            
            if not self.credentials.valid:
                # Si el token expiró, refrescarlo
                if self.credentials.expired and self.credentials.refresh_token:
                    logger.info("Token expirado, refrescando...")
                    self.credentials.refresh(Request())
            
            logger.info("Credenciales validadas correctamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al validar credenciales: {e}")
            return False
    
    def get_service_account_email(self) -> Optional[str]:
        """
        Obtiene el email de la Service Account.
        
        Útil para mostrar al usuario qué email debe agregar a sus calendarios.
        
        Returns:
            str: Email de la Service Account, o None si no hay credenciales cargadas
        """
        if self.credentials:
            return self.credentials.service_account_email
        
        # Si no hay credenciales cargadas, intentar leer el JSON directamente
        try:
            with open(self.credentials_path, 'r') as f:
                data = json.load(f)
                return data.get('client_email')
        except Exception as e:
            logger.error(f"Error al leer email de Service Account: {e}")
            return None
    
    def get_project_id(self) -> Optional[str]:
        """
        Obtiene el ID del proyecto de Google Cloud.
        
        Returns:
            str: ID del proyecto, o None si no se puede obtener
        """
        if self.credentials and hasattr(self.credentials, 'project_id'):
            return self.credentials.project_id
        
        # Intentar leer del JSON
        try:
            with open(self.credentials_path, 'r') as f:
                data = json.load(f)
                return data.get('project_id')
        except Exception as e:
            logger.error(f"Error al leer project_id: {e}")
            return None
