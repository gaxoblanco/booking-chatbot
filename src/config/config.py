"""
Configuration Module
====================
Loads and validates environment variables for WhatsApp bot.
Ensures all required credentials are present before starting.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """
    Configuration class for WhatsApp Bot
    Centralizes all environment variables and settings
    """

    # ==========================================
    # META CLOUD API
    # ==========================================
    META_PHONE_NUMBER_ID      = os.getenv('META_PHONE_NUMBER_ID')
    META_WHATSAPP_TOKEN       = os.getenv('META_WHATSAPP_TOKEN')
    META_APP_SECRET           = os.getenv('META_APP_SECRET')
    META_WEBHOOK_VERIFY_TOKEN = os.getenv('META_WEBHOOK_VERIFY_TOKEN')
    META_API_VERSION          = os.getenv('META_API_VERSION', 'v22.0')

    # ==========================================
    # FLASK SETTINGS
    # ==========================================
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))

    # ==========================================
    # WEBHOOK SETTINGS
    # ==========================================
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'http://localhost:5000')

    # ==========================================
    # FILE STORAGE
    # ==========================================
    CERTIFICATES_DIR = os.getenv('CERTIFICATES_DIR', './certificates')

    # ==========================================
    # ACCESO ADMINISTRATIVO
    # ==========================================

    # Clave maestra para operaciones de administración (testing, debug).
    # Los profesionales se cargan via CSV por el administrador — no hay
    # auto-registro desde WhatsApp. Esta clave NO es para profesionales.
    # En producción debe estar configurada o el sistema no arranca.
    MASTER_ACCESS_KEY = os.getenv('MASTER_ACCESS_KEY')
    if not MASTER_ACCESS_KEY and os.getenv('ENVIRONMENT') == 'production':
        raise ValueError(
            "[CONFIG] MASTER_ACCESS_KEY no configurada en producción. "
            "Generá una con: python -c \"import secrets; print(secrets.token_urlsafe(16))\""
        )

    ALLOW_KEY_REUSE = os.getenv('ALLOW_KEY_REUSE', 'false').lower() == 'true'

    # ==========================================
    # VALIDATION
    # ==========================================
    @staticmethod
    def validate():
        """
        Valida que todas las variables de entorno requeridas estén configuradas.
        Lanza ValueError si falta alguna — el servidor no arranca sin ellas.
        """
        required_vars = {
            'META_PHONE_NUMBER_ID':      Config.META_PHONE_NUMBER_ID,
            'META_WHATSAPP_TOKEN':       Config.META_WHATSAPP_TOKEN,
            'META_APP_SECRET':           Config.META_APP_SECRET,
            'META_WEBHOOK_VERIFY_TOKEN': Config.META_WEBHOOK_VERIFY_TOKEN,
        }

        missing_vars = [
            var_name for var_name, var_value in required_vars.items()
            if not var_value or var_value in ('XXXXXXX', '')
        ]

        if missing_vars:
            raise ValueError(
                f"Variables de entorno faltantes: {', '.join(missing_vars)}\n"
                f"Copiá .env.example a .env y completá las credenciales de Meta."
            )

        return True

    @staticmethod
    def print_config():
        """
        Imprime la configuración activa al arrancar (ocultando datos sensibles).
        """
        print("=" * 50)
        print("WHATSAPP BOT CONFIGURATION — Meta Cloud API")
        print("=" * 50)
        print(f"Environment:      {Config.FLASK_ENV}")
        print(f"Debug Mode:       {Config.FLASK_DEBUG}")
        print(f"Port:             {Config.FLASK_PORT}")
        print(f"Webhook URL:      {Config.WEBHOOK_URL}")
        print(f"Meta API version: {Config.META_API_VERSION}")
        print(f"Certificates Dir: {Config.CERTIFICATES_DIR}")

        # Datos sensibles — mostrar solo los primeros/últimos caracteres
        if Config.META_PHONE_NUMBER_ID:
            print(f"Phone Number ID:  {Config.META_PHONE_NUMBER_ID[:6]}... (parcial)")

        if Config.META_WHATSAPP_TOKEN:
            print(f"WhatsApp Token:   {'*' * 20} (hidden)")

        if Config.META_APP_SECRET:
            print(f"App Secret:       {'*' * 20} (hidden)")

        if Config.META_WEBHOOK_VERIFY_TOKEN:
            masked = Config.META_WEBHOOK_VERIFY_TOKEN[:4] + "..." 
            print(f"Verify Token:     {masked} (parcial)")

        print("=" * 50)


# Validate configuration on import (fails fast if misconfigured)
if __name__ != "__main__":
    try:
        Config.validate()
    except ValueError as e:
        print(f"\n⚠️  CONFIGURATION ERROR:\n{e}\n")
        # Don't exit, just warn - allows testing without full setup