"""
Reminder Integration Service
==============================
Ubicación: src/integrations/reminder/reminder_integration_service.py

Orquesta el ciclo completo de recordatorios como un servicio autónomo:

    1. send      — envía recordatorios diarios a las 17:30
    2. confirm   — auto-confirma los que no respondieron (+3hs)

El procesamiento de respuestas (1/2/0) sigue viviendo en:
    src/bot/reminder_handler.py  ← intercepta mensajes entrantes del bot

La conexión cancelación → waitlist está en reminder_handler._trigger_waitlist().

Este servicio reemplaza los jobs separados job_reminders y job_auto_confirm
en engine.py, agrupándolos bajo una única responsabilidad.

Uso desde engine.py:
    from src.integrations.reminder import reminder_integration_service
    # Reemplaza: job_reminders + job_auto_confirm
    reminder_integration_service.run_send_cycle()
    reminder_integration_service.run_confirm_cycle()
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class ReminderIntegrationService:
    """
    Servicio de integración para el ciclo completo de recordatorios.
    Desacoplado del flujo principal del bot — puede evolucionar de forma independiente.
    """

    # Horas sin respuesta antes de auto-confirmar
    AUTO_CONFIRM_TIMEOUT_HOURS = 3

    # =========================================================================
    # CICLO DE ENVÍO — job_reminders (17:30)
    # =========================================================================

    def run_send_cycle(self) -> Dict:
        """
        Envía recordatorios a todos los pacientes con turno mañana.
        Llamado por engine.py a las 17:30.

        Returns:
            { checked, sent, skipped, errors }
        """
        logger.info("[REMINDER-SVC] 🔔 Iniciando ciclo de envío")
        try:
            from src.services.reminder_service import reminder_service
            stats = reminder_service.send_daily_reminders()
            logger.info(f"[REMINDER-SVC] ✅ Envío completado: {stats}")
            return stats
        except Exception as e:
            logger.error(f"[REMINDER-SVC] ❌ Error en ciclo de envío: {e}")
            return {"checked": 0, "sent": 0, "skipped": 0, "errors": 1, "error_detail": str(e)}

    # =========================================================================
    # CICLO DE CONFIRMACIÓN — job_auto_confirm (20:30)
    # =========================================================================

    def run_confirm_cycle(self) -> Dict:
        """
        Auto-confirma los recordatorios sin respuesta pasado el timeout.
        Llamado por engine.py 3 horas después del envío.

        Returns:
            { checked, confirmed, errors, appointments }
        """
        logger.info(f"[REMINDER-SVC] ⏱️  Iniciando ciclo de auto-confirm ({self.AUTO_CONFIRM_TIMEOUT_HOURS}h timeout)")
        try:
            from src.services.reminder_service import reminder_service
            stats = reminder_service.auto_confirm_unanswered(
                timeout_hours=self.AUTO_CONFIRM_TIMEOUT_HOURS
            )
            logger.info(f"[REMINDER-SVC] ✅ Auto-confirm completado: {stats}")
            return stats
        except Exception as e:
            logger.error(f"[REMINDER-SVC] ❌ Error en ciclo de auto-confirm: {e}")
            return {"checked": 0, "confirmed": 0, "errors": 1, "appointments": [], "error_detail": str(e)}

    # =========================================================================
    # DISPARO MANUAL — para testing y comando secreto del bot
    # =========================================================================

    def trigger_now(self) -> Dict:
        """
        Ejecuta el ciclo de envío de forma inmediata.
        Usado por el comando secreto del bot y para testing.

        Returns:
            Stats del envío con campo 'message' para responder al admin.
        """
        logger.info("[REMINDER-SVC] 🔔 Disparo manual solicitado")
        stats = self.run_send_cycle()

        sent    = stats.get('sent', 0)
        checked = stats.get('checked', 0)
        errors  = stats.get('errors', 0)

        if checked == 0:
            message = "📭 No hay citas para mañana."
        elif sent == 0:
            message = (
                f"⚠️ Se revisaron {checked} cita(s) pero no se enviaron recordatorios.\n"
                "Verificá que TWILIO_REMINDER_TEMPLATE_SID esté configurado."
            )
        else:
            message = (
                f"✅ Recordatorios enviados: {sent}/{checked}."
                + (f"\n⚠️ Errores: {errors}." if errors else "")
            )

        return {**stats, 'message': message}


# Instancia global
reminder_integration_service = ReminderIntegrationService()