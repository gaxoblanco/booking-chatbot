"""
Handler de Respuestas a Recordatorios
======================================

Integra las respuestas de recordatorios con el bot principal.

Se integra en bot_controller.py para detectar cuando un cliente
está respondiendo a un recordatorio.

Author: Salud Conecta
"""

from src.services.reminder_service import reminder_service
from src.core.states import SessionData, ConversationState
import logging

logger = logging.getLogger(__name__)


def should_handle_as_reminder(session: SessionData, message: str) -> bool:
    """
    Determina si el mensaje debería manejarse como respuesta a recordatorio.
    
    Criterios:
    1. Estado es AWAITING_REMINDER_RESPONSE
    2. O el mensaje es 1/2/0 y hay un recordatorio pendiente
    
    Args:
        session: Sesión del usuario
        message: Mensaje recibido
    
    Returns:
        True si debe manejarse como respuesta a recordatorio
    """
    # Caso 1: Estado explícito
    if session.state == ConversationState.AWAITING_REMINDER_RESPONSE:
        return True
    
    # Caso 2: Mensaje es 1, 2 o 0 y hay recordatorio pendiente
    if message in ['1', '2', '0']:
        reminder = reminder_service._get_pending_reminder(session.phone_number)
        if reminder:
            logger.info(f"[REMINDER] Detectado recordatorio pendiente para {session.phone_number}")
            return True
    
    return False


def handle_reminder_response(session: SessionData, message: str) -> str:
    """
    Maneja la respuesta del cliente a un recordatorio.

    Args:
        session: Sesión del usuario
        message: Respuesta ("1", "2" o "0")

    Returns:
        Mensaje de respuesta para el cliente
    """
    logger.info(f"[REMINDER] Procesando respuesta '{message}' de {session.phone_number}")

    result = reminder_service.handle_reminder_response(
        client_phone=session.phone_number,
        response=message
    )

    if not result['success']:
        return result.get('message', "Error procesando tu respuesta.")

    action = result.get('action')

    # OPCIÓN 1: CONFIRMADO
    if action == 'confirmed':
        session.clear_temp()
        session.transition_to(ConversationState.CLIENT_MAIN_MENU)
        return result['message']

    # OPCIÓN 2: REPROGRAMAR
    elif action == 'reschedule':
        session.transition_to(ConversationState.CLIENT_RESCHEDULE_APPOINTMENT)
        reminder = reminder_service._get_pending_reminder(session.phone_number)
        if reminder:
            apt_id = reminder['appointment_id']
            session.store_temp('appointment_id', apt_id)

            # El turno original queda libre al reprogramar → ofrecer a waitlist
            import threading
            threading.Thread(
                target=_trigger_waitlist,
                args=(apt_id, "cancelled"),
                daemon=True,
                name=f"waitlist-reminder-{apt_id}"
            ).start()

        return result['message']

    # OPCIÓN 0: CANCELAR — conecta automáticamente con waitlist
    elif action == 'cancel':
        session.transition_to(ConversationState.CLIENT_CANCEL_APPOINTMENT)
        reminder = reminder_service._get_pending_reminder(session.phone_number)
        if reminder:
            apt_id = reminder['appointment_id']
            session.store_temp('appointment_id', apt_id)

            # Disparar waitlist en hilo separado — no bloquea la respuesta al paciente
            import threading
            from src.services.waitlist_service import waitlist_service
            threading.Thread(
                target=_trigger_waitlist,
                args=(apt_id,),
                daemon=True,
                name=f"waitlist-reminder-{apt_id}"
            ).start()

        return result['message']

    else:
        return "Error procesando tu respuesta. Por favor, intenta nuevamente."


def _trigger_waitlist(appointment_id: int, reason: str = "cancelled") -> None:
        """
        Dispara waitlist para un turno liberado desde un recordatorio.
        Corre en hilo separado para no bloquear la respuesta WhatsApp.

        Args:
            appointment_id: ID de la cita que quedó libre
            reason: 'cancelled' | 'rescheduled'
        """
        try:
            from src.services.waitlist_service import waitlist_service
            logger.info(f"[REMINDER→WAITLIST] Slot liberado por '{reason}' — cita #{appointment_id}")
            result = waitlist_service.handle_slot_freed(
                freed_appointment_id=appointment_id,
                reason=reason
            )
            logger.info(f"[REMINDER→WAITLIST] Resultado: {result}")
        except Exception as e:
            logger.error(f"[REMINDER→WAITLIST] Error procesando waitlist para #{appointment_id}: {e}")

# =========================================================================
# INTEGRACIÓN CON BOT_CONTROLLER
# =========================================================================

"""
CÓMO INTEGRAR EN bot_controller.py:

1. Importar en bot_controller.py:
    from src.bot.reminder_handler import should_handle_as_reminder, handle_reminder_response

2. En process_message(), ANTES de routing normal:
    
    # ⭐ PRIORIDAD: Verificar si es respuesta a recordatorio
    if should_handle_as_reminder(session, message):
        return handle_reminder_response(session, message)
    
    # Routing normal continúa...

3. Agregar estado en ConversationState (models/session.py):
    AWAITING_REMINDER_RESPONSE = "awaiting_reminder_response"

Ejemplo completo:

def process_message(self, phone_number: str, message: str) -> str:
    session = self.session_manager.get_session(phone_number)
    
    # ⭐ NUEVO: Manejar recordatorios con prioridad
    if should_handle_as_reminder(session, message):
        return handle_reminder_response(session, message)
    
    # Routing normal
    handler = self._get_handler_for_state(session.state)
    return handler(session, message)
"""
