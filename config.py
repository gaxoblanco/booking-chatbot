"""
Configuration Module
====================
Loads and validates environment variables for WhatsApp bot.
Ensures all required credentials are present before starting.

Updated to use Meta WhatsApp Cloud API instead of Twilio.
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
    # META WHATSAPP CLOUD API CREDENTIALS
    # ==========================================
    META_WHATSAPP_TOKEN = os.getenv('META_WHATSAPP_TOKEN')
    META_PHONE_NUMBER_ID = os.getenv('META_PHONE_NUMBER_ID')
    META_WHATSAPP_BUSINESS_ACCOUNT_ID = os.getenv(
        'META_WHATSAPP_BUSINESS_ACCOUNT_ID')
    META_WEBHOOK_VERIFY_TOKEN = os.getenv('META_WEBHOOK_VERIFY_TOKEN')

    # Meta API Base URL
    META_API_VERSION = 'v21.0'
    META_API_BASE_URL = f'https://graph.facebook.com/{META_API_VERSION}'

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
    # VALIDATION
    # ==========================================
    @staticmethod
    def validate():
        """
        Validate that all required environment variables are set.
        Raises ValueError if any required variable is missing.
        """
        required_vars = {
            'META_WHATSAPP_TOKEN': Config.META_WHATSAPP_TOKEN,
            'META_PHONE_NUMBER_ID': Config.META_PHONE_NUMBER_ID,
            'META_WEBHOOK_VERIFY_TOKEN': Config.META_WEBHOOK_VERIFY_TOKEN,
        }

        missing_vars = [
            var_name for var_name, var_value in required_vars.items()
            if not var_value
        ]

        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}\n"
                f"Please copy .env.example to .env and fill in your Meta WhatsApp Cloud API credentials."
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
        print(f"Certificates Dir: {Config.CERTIFICATES_DIR}")
        print(f"API Provider: Meta WhatsApp Cloud API")

        # Hide sensitive data
        if Config.META_PHONE_NUMBER_ID:
            print(f"Phone Number ID: {Config.META_PHONE_NUMBER_ID}")

        if Config.META_WHATSAPP_BUSINESS_ACCOUNT_ID:
            print(
                f"WhatsApp Business Account ID: {Config.META_WHATSAPP_BUSINESS_ACCOUNT_ID}")

        if Config.META_WHATSAPP_TOKEN:
            masked_token = Config.META_WHATSAPP_TOKEN[:10] + \
                "..." + Config.META_WHATSAPP_TOKEN[-10:]
            print(f"Access Token: {masked_token}")

        if Config.META_WEBHOOK_VERIFY_TOKEN:
            print(f"Webhook Verify Token: {'*' * 20} (hidden)")

        print("=" * 50)


# Validate configuration on import (fails fast if misconfigured)
if __name__ != "__main__":
    try:
        Config.validate()
    except ValueError as e:
        print(f"\n⚠️  CONFIGURATION ERROR:\n{e}\n")
        # Don't exit, just warn - allows testing without full setup
