"""
Twilio Service — Stub
=====================
Ubicación: src/integrations/twilio_service.py

Servicio opcional para notificaciones WhatsApp a profesionales.
Activar con NOTIFY_PROFESSIONAL=true en el .env cuando se quiera usar.

Por ahora deshabilitado — las notificaciones al profesional
se gestionan manualmente o por otro canal.
"""

import os
import logging

logger = logging.getLogger(__name__)

NOTIFY_ENABLED = os.getenv("NOTIFY_PROFESSIONAL", "false").lower() == "true"


def notify_professional(professional_phone: str, message: str) -> bool:
    """
    Envía notificación WhatsApp al profesional.

    Args:
        professional_phone: Teléfono del profesional
        message: Mensaje a enviar

    Returns:
        True si se envió, False si está deshabilitado o falló
    """
    if not NOTIFY_ENABLED:
        logger.debug(
            f"[TWILIO_SERVICE] Notificación deshabilitada "
            f"(NOTIFY_PROFESSIONAL=false) — omitiendo para {professional_phone}"
        )
        return False

    # Implementar cuando se quiera activar
    # from twilio.rest import Client
    # client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
    # ...
    logger.warning("[TWILIO_SERVICE] NOTIFY_PROFESSIONAL=true pero el servicio no está implementado")
    return False


def send_whatsapp(to: str, message: str) -> bool:
    """Alias de notify_professional para compatibilidad."""
    return notify_professional(to, message)


class TwilioService:
    """Clase stub para compatibilidad con imports que usen TwilioService()."""

    def send_message(self, to: str, message: str) -> bool:
        return notify_professional(to, message)

    def notify_professional(self, professional_phone: str, message: str) -> bool:
        return notify_professional(professional_phone, message)


# Instancia global
twilio_service = TwilioService()