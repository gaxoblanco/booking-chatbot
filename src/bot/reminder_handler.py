"""
Handler de Respuestas a Recordatorios
======================================

Integra las respuestas de recordatorios con el bot principal.

Author: Salud Conecta

CAMBIOS v1.1
------------
PROBLEMA DETECTADO (log 2026-04-06):
  - La sesión expira entre el envío del recordatorio y la respuesta
    del paciente → state == 'start' en lugar de AWAITING_REMINDER_RESPONSE.
  - El NLU intercepta "confirmo" ANTES del reminder handler
    y lo clasifica como Intent.GREETING → el paciente ve el menú principal.

SOLUCIÓN:
  1. should_handle_as_reminder() ya no depende del estado de sesión:
     consulta directamente la BD buscando recordatorio pendiente.
  2. normalize_reminder_response() convierte texto libre ('sí', 'confirmo',
     'cancelo', etc.) al código canónico '1', '2' o '0'.
  3. ⚠️  La integración en bot_controller debe ocurrir ANTES del pipeline NLU.
"""

import unicodedata
import threading
import logging

from src.services.reminder_service import reminder_service
from src.core.states import SessionData, ConversationState

logger = logging.getLogger(__name__)


# =========================================================================
# PASO 1 — NORMALIZACIÓN DE RESPUESTAS
# =========================================================================
#
# Mapa de variantes → código canónico.
#
# Reglas de matching:
#   - Todo se convierte a minúsculas y sin tildes antes de comparar.
#   - Se busca si ALGUNA keyword está CONTENIDA en el mensaje limpio.
#     Ejemplo: "sí, confirmo el turno" → contiene 'confirmo' → '1'
#
# Orden de prioridad al chequear:
#   reprogramar > confirmar > cancelar
#   Razón: "no, quiero reprogramar" contiene 'no' (cancel) pero la
#   intención real es reprogramar → reprogramar tiene mayor prioridad.

_RESCHEDULE_KEYWORDS = frozenset({
    '2',
    'cambiar',
    'cambio',
    'cambia',
    'reprogramar',
    'reprogramo',
    'otro dia',     # 'otro día' sin tilde
    'otro horario',
    'mover',
    'postergar',
    'mas tarde',    # 'más tarde'
    'despues',      # 'después'
})

_CONFIRM_KEYWORDS = frozenset({
    '1',
    'si',           # 'sí' sin tilde
    'ok',
    'dale',
    'confirmo',
    'confirmar',
    'confirmado',
    'bien',
    'voy',
    'ahi voy',      # 'ahí voy'
    'perfecto',
    'listo',
    'bueno',
    'claro',
    'obvio',
    'seguro',
    'va',
})

_CANCEL_KEYWORDS = frozenset({
    '0',
    'no',
    'cancelar',
    'cancelo',
    'no voy',
    'no puedo',
    'me cancelo',
    'borro',
    'borrar',
    'eliminar',
})


def _strip_accents(text: str) -> str:
    """
    Elimina tildes y diacríticos de un texto unicode.
    Ejemplo: 'Sí, confirmo' → 'Si, confirmo'
    """
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def normalize_reminder_response(message: str) -> str | None:
    """
    Convierte texto libre del paciente en código canónico para reminder_service.

    Acepta variantes naturales en castellano rioplatense, con o sin tildes,
    con puntuación y espacios variables.

    Args:
        message: Texto crudo recibido por WhatsApp. Ejemplos:
                 "Sí", "confirmo", "1", "quiero cambiar el horario", "no puedo ir"

    Returns:
        '1'  → confirmar asistencia
        '2'  → reprogramar / cambiar horario
        '0'  → cancelar turno
        None → no se reconoció ninguna intención válida
    """
    # --- Limpiar texto ---
    clean = _strip_accents(message.lower().strip())

    # Eliminar puntuación que no aporta significado semántico
    for char in '.,!?¡¿:;':
        clean = clean.replace(char, '')

    # Colapsar espacios múltiples
    clean = ' '.join(clean.split())

    logger.debug(f"[REMINDER][NORMALIZE] '{message}' → '{clean}'")

    # --- Reprogramar tiene prioridad más alta ---
    # (evita falso positivo de 'no' en "no, quiero reprogramar")
    for kw in _RESCHEDULE_KEYWORDS:
        if kw in clean:
            logger.info(f"[REMINDER][NORMALIZE] '{message}' → '2' (kw: '{kw}')")
            return '2'

    # --- Confirmar ---
    for kw in _CONFIRM_KEYWORDS:
        if kw in clean:
            logger.info(f"[REMINDER][NORMALIZE] '{message}' → '1' (kw: '{kw}')")
            return '1'

    # --- Cancelar ---
    for kw in _CANCEL_KEYWORDS:
        if kw in clean:
            logger.info(f"[REMINDER][NORMALIZE] '{message}' → '0' (kw: '{kw}')")
            return '0'

    logger.info(f"[REMINDER][NORMALIZE] '{message}' → None (no reconocido)")
    return None


# =========================================================================
# PASO 2 — DETECCIÓN DE RECORDATORIO PENDIENTE
# =========================================================================

def should_handle_as_reminder(session: SessionData, message: str) -> bool:
    """
    Determina si el mensaje debe tratarse como respuesta a un recordatorio.

    Tres capas de validación en orden:
      1. Ventana de tiempo: solo entre REMINDER_SEND_TIME y REMINDER_CLOSE_TIME
      2. Sesión sin flujo activo: no interceptar si el paciente está en medio de algo
      3. Reminder pendiente en BD + mensaje normalizable
    """
    from datetime import datetime
    import os

    # -----------------------------------------------------------------
    # CAPA 1 — Ventana de tiempo
    # -----------------------------------------------------------------

    def _parse_time_env(var: str, default: str) -> int:
        """Convierte 'HH:MM' del .env a minutos desde medianoche."""
        raw = os.getenv(var, default)
        try:
            h, m = raw.split(":")
            return int(h) * 60 + int(m)
        except Exception:
            logger.warning(f"[REMINDER] {var} inválido: '{raw}' — usando {default}")
            h, m = default.split(":")
            return int(h) * 60 + int(m)

    now_minutes   = datetime.now().hour * 60 + datetime.now().minute
    open_minutes  = _parse_time_env("REMINDER_SEND_TIME",  "17:30")
    close_minutes = _parse_time_env("REMINDER_CLOSE_TIME", "20:30")

    if not (open_minutes <= now_minutes <= close_minutes):
        return False

    # -----------------------------------------------------------------
    # CAPA 2 — Sesión sin flujo activo
    # Si el paciente está en medio de otra cosa, no interceptar
    # -----------------------------------------------------------------
    _NEUTRAL_STATES = {
        ConversationState.START,
        ConversationState.CLIENT_MAIN_MENU,
        ConversationState.CLIENT_NEW_USER_MENU,
        ConversationState.AWAITING_REMINDER_RESPONSE,
    }
    if session.state not in _NEUTRAL_STATES:
        return False

    # -----------------------------------------------------------------
    # CAPA 3 — Reminder pendiente en BD + mensaje reconocible
    # -----------------------------------------------------------------
    # Caso rápido: estado explícito de espera
    if session.state == ConversationState.AWAITING_REMINDER_RESPONSE:
        return True

    # Sesión neutral o expirada: consultar BD solo si el mensaje normaliza
    normalized = normalize_reminder_response(message)
    if normalized is None:
        return False

    reminder = reminder_service._get_pending_reminder(session.phone_number)
    if reminder:
        logger.info(
            f"[REMINDER] Interceptado — ventana activa, sesión neutral, "
            f"reminder en BD, mensaje='{message}'→'{normalized}'"
        )
        return True

    return False

# =========================================================================
# PASO 3 — PROCESAMIENTO DE LA RESPUESTA
# =========================================================================

def handle_reminder_response(session: SessionData, message: str) -> str:
    """
    Maneja la respuesta del paciente a un recordatorio.

    Normaliza el mensaje antes de pasarlo al reminder_service,
    aceptando tanto códigos numéricos como texto libre en español.

    Args:
        session: Sesión del usuario.
        message: Respuesta cruda del paciente.

    Returns:
        Mensaje de respuesta para enviar al paciente por WhatsApp.
    """
    # Normalizar texto libre → código canónico
    normalized = normalize_reminder_response(message)

    # No se reconoció — pedir aclaración
    if normalized is None:
        logger.warning(
            f"[REMINDER] Respuesta no reconocida '{message}' "
            f"de {session.phone_number}"
        )
        return (
            "No entendí tu respuesta. 😕\n\n"
            "Respondé con:\n"
            "1️⃣ *1* — Confirmar que vas\n"
            "2️⃣ *2* — Cambiar el horario\n"
            "0️⃣ *0* — Cancelar el turno"
        )

    logger.info(
        f"[REMINDER] Procesando '{message}' → '{normalized}' "
        f"de {session.phone_number}"
    )

    # Delegar al servicio con el código normalizado
    result = reminder_service.handle_reminder_response(
        client_phone=session.phone_number,
        response=normalized
    )

    if not result['success']:
        return result.get('message', "Error procesando tu respuesta. Intentá de nuevo.")

    action = result.get('action')

    # --- OPCIÓN 1: CONFIRMAR ---
    if action == 'confirmed':
        session.clear_temp()
        session.transition_to(ConversationState.CLIENT_MAIN_MENU)
        return result['message']

    # --- OPCIÓN 2: REPROGRAMAR ---
    elif action == 'reschedule':
        session.transition_to(ConversationState.CLIENT_RESCHEDULE_APPOINTMENT)
        reminder = reminder_service._get_pending_reminder(session.phone_number)
        if reminder:
            apt_id = reminder['appointment_id']
            session.store_temp('appointment_id', apt_id)
            # Liberar slot para waitlist — hilo separado para no bloquear respuesta
            threading.Thread(
                target=_trigger_waitlist,
                args=(apt_id, 'rescheduled'),
                daemon=True,
                name=f"waitlist-reminder-{apt_id}"
            ).start()
        return result['message']

    # --- OPCIÓN 0: CANCELAR ---
    elif action == 'cancel':
        session.transition_to(ConversationState.CLIENT_CANCEL_APPOINTMENT)
        reminder = reminder_service._get_pending_reminder(session.phone_number)
        if reminder:
            apt_id = reminder['appointment_id']
            session.store_temp('appointment_id', apt_id)
            # Notificar waitlist — hilo separado
            threading.Thread(
                target=_trigger_waitlist,
                args=(apt_id, 'cancelled'),
                daemon=True,
                name=f"waitlist-reminder-{apt_id}"
            ).start()
        return result['message']

    else:
        logger.error(f"[REMINDER] Acción desconocida: '{action}'")
        return "Error procesando tu respuesta. Por favor, intentá nuevamente."


# =========================================================================
# PASO 4 — WAITLIST (sin cambios respecto a v1.0)
# =========================================================================

def _trigger_waitlist(appointment_id: int, reason: str = 'cancelled') -> None:
    """
    Dispara la lógica de waitlist para un slot liberado.
    Corre en hilo separado para no bloquear la respuesta WhatsApp.

    Args:
        appointment_id: ID de la cita que quedó libre.
        reason: 'cancelled' | 'rescheduled'
    """
    try:
        from src.services.waitlist_service import waitlist_service
        logger.info(
            f"[REMINDER→WAITLIST] Slot liberado por '{reason}' "
            f"— cita #{appointment_id}"
        )
        result = waitlist_service.handle_slot_freed(
            freed_appointment_id=appointment_id,
            reason=reason
        )
        logger.info(f"[REMINDER→WAITLIST] Resultado: {result}")
    except Exception as e:
        logger.error(
            f"[REMINDER→WAITLIST] Error en waitlist para #{appointment_id}: {e}"
        )


# =========================================================================
# INTEGRACIÓN EN bot_controller.py
# =========================================================================
"""
⚠️  CRÍTICO: el chequeo de recordatorio debe ir ANTES del pipeline NLU.

Causa del bug: "Confirmo" pasaba por NLU → Intent.GREETING → menú principal.
El reminder handler nunca se ejecutaba.

CAMBIO EN bot_controller.py — método process_message():

    from src.bot.reminder_handler import (
        should_handle_as_reminder,
        handle_reminder_response,
    )

    def process_message(self, phone_number: str, message: str) -> str:
        session = self.session_manager.get_session(phone_number)

        # ⭐ ANTES DEL NLU — chequear recordatorio pendiente
        # Funciona aunque la sesión haya expirado (consulta BD directamente)
        if should_handle_as_reminder(session, message):
            return handle_reminder_response(session, message)

        # Pipeline NLU normal — sin cambios
        intent = self.nlu.process(message)
        handler = self._get_handler_for_intent(session, intent)
        return handler(session, message)
"""