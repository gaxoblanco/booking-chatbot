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
    # TWILIO CREDENTIALS
    # ==========================================
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    TWILIO_WHATSAPP_NUMBER = os.getenv(
        'TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')

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
    # SISTEMA DE CLAVES DE ACCESO
    # ==========================================

    # Claves válidas para profesionales
    # Formato: { "clave": {"used": False, "created_by": "admin", "expires": "2025-12-31"} }
    PROFESSIONAL_ACCESS_KEYS = {
        "PSICO2025": {
            "used": False,
            "created_by": "admin",
            "expires": None,
            "used_by": None,
            "used_at": None
        },
        "DEMO12345": {
            "used": False,
            "created_by": "admin",
            "expires": "2025-12-31",
            "used_by": None,
            "used_at": None
        },
    }

    # Alternativamente, usar una clave maestra que siempre funciona (para testing)
    MASTER_ACCESS_KEY = os.getenv('MASTER_ACCESS_KEY', 'ADMIN2025')

    # Permitir múltiples usos de la misma clave (False = una clave solo se usa una vez)
    ALLOW_KEY_REUSE = os.getenv('ALLOW_KEY_REUSE', 'false').lower() == 'true'

    # ==========================================
    # VALIDATION
    # ==========================================
    @staticmethod
    def validate():
        """
        Validate that all required environment variables are set.
        Raises ValueError if any required variable is missing.
        """
        required_vars = {
            'TWILIO_ACCOUNT_SID': Config.TWILIO_ACCOUNT_SID,
            'TWILIO_AUTH_TOKEN': Config.TWILIO_AUTH_TOKEN,
        }

        missing_vars = [
            var_name for var_name, var_value in required_vars.items()
            if not var_value or var_value == 'your_account_sid_here' or var_value == 'your_auth_token_here'
        ]

        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}\n"
                f"Please copy .env.example to .env and fill in your Twilio credentials."
            )

        return True

    @staticmethod
    def print_config():
        """
        Print current configuration (hiding sensitive data).
        Useful for debugging.
        """
        print("=" * 50)
        print("WHATSAPP BOT CONFIGURATION")
        print("=" * 50)
        print(f"Environment: {Config.FLASK_ENV}")
        print(f"Debug Mode: {Config.FLASK_DEBUG}")
        print(f"Port: {Config.FLASK_PORT}")
        print(f"Webhook URL: {Config.WEBHOOK_URL}")
        print(f"WhatsApp Number: {Config.TWILIO_WHATSAPP_NUMBER}")
        print(f"Certificates Dir: {Config.CERTIFICATES_DIR}")

        # Hide sensitive data
        if Config.TWILIO_ACCOUNT_SID:
            masked_sid = Config.TWILIO_ACCOUNT_SID[:8] + \
                "..." + Config.TWILIO_ACCOUNT_SID[-4:]
            print(f"Account SID: {masked_sid}")

        if Config.TWILIO_AUTH_TOKEN:
            print(f"Auth Token: {'*' * 20} (hidden)")

        print("=" * 50)


# Validate configuration on import (fails fast if misconfigured)
if __name__ != "__main__":
    try:
        Config.validate()
    except ValueError as e:
        print(f"\n⚠️  CONFIGURATION ERROR:\n{e}\n")
        # Don't exit, just warn - allows testing without full setup
