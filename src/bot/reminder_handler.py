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
    
    # Procesar respuesta
    result = reminder_service.handle_reminder_response(
        client_phone=session.phone_number,
        response=message
    )
    
    if not result['success']:
        return result.get('message', "Error procesando tu respuesta.")
    
    # Manejar según acción
    action = result.get('action')
    
    # OPCIÓN 1: CONFIRMADO
    if action == 'confirmed':
        # Limpiar estado y volver al menú
        session.clear_temp()
        session.transition_to(ConversationState.CLIENT_MAIN_MENU)
        
        return result['message']
    
    # OPCIÓN 2: REPROGRAMAR
    elif action == 'reschedule':
        # Transicionar a flujo de reprogramación
        session.transition_to(ConversationState.CLIENT_RESCHEDULE_APPOINTMENT)
        
        # Guardar appointment_id en temp
        reminder = reminder_service._get_pending_reminder(session.phone_number)
        if reminder:
            session.store_temp('appointment_id', reminder['appointment_id'])
        
        return result['message']
    
    # OPCIÓN 0: CANCELAR
    elif action == 'cancel':
        # Transicionar a confirmación de cancelación
        session.transition_to(ConversationState.CLIENT_CANCEL_APPOINTMENT)
        
        # Guardar appointment_id en temp
        reminder = reminder_service._get_pending_reminder(session.phone_number)
        if reminder:
            session.store_temp('appointment_id', reminder['appointment_id'])
        
        return result['message']
    
    else:
        return "Error procesando tu respuesta. Por favor, intenta nuevamente."


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
