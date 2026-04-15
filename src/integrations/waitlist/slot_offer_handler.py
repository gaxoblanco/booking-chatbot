"""
Slot Offer Handler
==================
Intercepta y procesa respuestas de clientes a ofertas de adelantamiento
de turno (waitlist). Análogo a reminder_handler.py.

Flujo:
    1. bot_controller llama should_handle_as_slot_offer() antes del NLU
    2. Si hay oferta pending activa → handle_slot_offer_response()
    3. "1" acepta, "2" rechaza, cualquier otro → repregunta sin romper estado
    4. Si la oferta expiró → informa y libera sesión
"""

import logging
from datetime import datetime
from typing import Optional

from src.core.states import ConversationState, SessionData
from src.services.waitlist_service import waitlist_service
from src.messages.loader import get_msg

logger = logging.getLogger(__name__)


# ── Helpers de formato de fecha ───────────────────────────────────────────────

_DIAS  = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
_MESES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
          'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']


def _fmt_date(date_str: str) -> str:
    """Convierte 'YYYY-MM-DD' → 'Lunes 16 de Abril de 2026'."""
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d')
        return f"{_DIAS[d.weekday()]} {d.day} de {_MESES[d.month - 1]} de {d.year}"
    except Exception:
        return date_str  # fallback: mostrar crudo


# ── Detección ─────────────────────────────────────────────────────────────────

def should_handle_as_slot_offer(session: SessionData, message: str) -> bool:
    """
    Devuelve True si el cliente tiene una oferta de adelantamiento pendiente.

    Consulta BD directamente — no depende del estado de sesión ni de Redis.
    Si encuentra oferta activa, fuerza el estado AWAITING_SLOT_OFFER.

    Llamado desde bot_controller ANTES del NLU, inmediatamente después
    de should_handle_as_reminder().
    """
    try:
        offer = waitlist_service._get_pending_offer(session.phone_number)

        if offer:
            # Forzar estado aunque la sesión haya sido recreada
            if session.state != ConversationState.AWAITING_SLOT_OFFER:
                session.transition_to(ConversationState.AWAITING_SLOT_OFFER)
                logger.info(
                    f"[SLOT-OFFER] Oferta pending detectada para "
                    f"{session.phone_number} → AWAITING_SLOT_OFFER"
                )
            return True

        return False

    except Exception as e:
        logger.error(f"[SLOT-OFFER] Error en should_handle_as_slot_offer: {e}")
        return False


# ── Handler principal ─────────────────────────────────────────────────────────

def handle_slot_offer_response(session: SessionData, message: str) -> str:
    """
    Procesa la respuesta del cliente a una oferta de adelantamiento.

    Estados de salida:
        - Acepta (1)  → CLIENT_MAIN_MENU
        - Rechaza (2) → CLIENT_MAIN_MENU
        - Expirada    → CLIENT_MAIN_MENU
        - Inválido    → AWAITING_SLOT_OFFER (repregunta)
    """
    client_phone = session.phone_number

    # Normalizar texto libre → 1 o 2
    _msg = message.strip().lower()
    if _msg in ('1', 'si', 'sí', 's', 'dale', 'acepto', 'ok'):
        message = '1'
    elif _msg in ('2', 'no', 'n', 'nope', 'rechazar', 'mantener'):
        message = '2'

    # Obtener oferta pendiente
    offer = waitlist_service._get_pending_offer(client_phone)

    if not offer:
        # Sin oferta — limpiar estado y continuar normalmente
        session.clear_temp()
        session.transition_to(ConversationState.CLIENT_MAIN_MENU)
        return None  # bot_controller seguirá el flujo normal

    # Verificar expiración
    if datetime.now() > datetime.fromisoformat(offer['expires_at']):
        waitlist_service._mark_offer_expired(offer['id'])
        session.clear_temp()
        session.transition_to(ConversationState.CLIENT_MAIN_MENU)

        # Obtener datos del turno actual para el mensaje
        original_apt = waitlist_service.db.get_appointment(
            offer['original_appointment_id']
        )
        return _build_expired_msg(offer, original_apt)

    # ── Procesar respuesta ────────────────────────────────────────────────────

    if message == '1':
        result = waitlist_service.handle_offer_response(client_phone, '1')
        session.clear_temp()
        session.transition_to(ConversationState.CLIENT_MAIN_MENU)

        if result.get('success'):
            return _build_accepted_msg(offer, result)
        else:
            return get_msg('ERROR_GENERIC') or "❌ No pudimos mover el turno. Intentá de nuevo."

    elif message == '2':
        result = waitlist_service.handle_offer_response(client_phone, '2')
        session.clear_temp()
        session.transition_to(ConversationState.CLIENT_MAIN_MENU)

        original_apt = waitlist_service.db.get_appointment(
            offer['original_appointment_id']
        )
        return _build_rejected_msg(offer, original_apt)

    else:
        # Respuesta no reconocida — mantener estado, calcular tiempo restante
        return _build_invalid_msg(offer)


# ── Constructores de mensajes ─────────────────────────────────────────────────

def _build_accepted_msg(offer: dict, result: dict) -> str:
    """Mensaje de turno adelantado exitosamente."""
    prof_name = offer.get('professional_name') or 'el profesional'
    new_date  = _fmt_date(offer['freed_date'])
    new_time  = offer['freed_time']

    tpl = get_msg('SLOT_OFFER_ACCEPTED')
    if tpl:
        return tpl.format(
            prof_name=prof_name,
            new_date=new_date,
            new_time=new_time,
        )
    # Fallback si el tono no tiene la constante aún
    return (
        f"✅ Turno adelantado.\n\n"
        f"👨‍⚕️ {prof_name}\n"
        f"📅 {new_date} a las {new_time} hs\n\n"
        f"Tu turno anterior quedó cancelado. ¡Te esperamos!"
    )


def _build_rejected_msg(offer: dict, original_apt: Optional[dict]) -> str:
    """Mensaje de turno mantenido."""
    prof_name    = offer.get('professional_name') or 'el profesional'
    current_date = _fmt_date(original_apt['appointment_date']) if original_apt else '—'
    current_time = original_apt['start'] if original_apt else '—'

    tpl = get_msg('SLOT_OFFER_REJECTED')
    if tpl:
        return tpl.format(
            prof_name=prof_name,
            current_date=current_date,
            current_time=current_time,
        )
    return (
        f"👍 Perfecto. Mantenemos tu turno:\n\n"
        f"👨‍⚕️ {prof_name}\n"
        f"📅 {current_date} a las {current_time} hs\n\n"
        f"¡Te esperamos!"
    )


def _build_expired_msg(offer: dict, original_apt: Optional[dict]) -> str:
    """Mensaje de oferta expirada."""
    prof_name    = offer.get('professional_name') or 'el profesional'
    current_date = _fmt_date(original_apt['appointment_date']) if original_apt else '—'
    current_time = original_apt['start'] if original_apt else '—'

    tpl = get_msg('SLOT_OFFER_EXPIRED')
    if tpl:
        return tpl.format(
            prof_name=prof_name,
            current_date=current_date,
            current_time=current_time,
        )
    return (
        f"⏰ El turno ya fue tomado.\n\n"
        f"Tu turno sigue en pie:\n"
        f"👨‍⚕️ {prof_name}\n"
        f"📅 {current_date} a las {current_time} hs\n\n"
        f"¡Te esperamos!"
    )


def _build_invalid_msg(offer: dict) -> str:
    """Mensaje de respuesta no reconocida — no rompe el estado."""
    # Calcular minutos restantes
    try:
        delta = datetime.fromisoformat(offer['expires_at']) - datetime.now()
        minutes_left = max(1, int(delta.total_seconds() // 60))
    except Exception:
        minutes_left = '?'

    tpl = get_msg('SLOT_OFFER_INVALID')
    if tpl:
        return tpl.format(minutes_left=minutes_left)
    return (
        f"No entendí tu respuesta.\n\n"
        f"1️⃣ Sí, adelanto el turno\n"
        f"2️⃣ No, mantengo el mío\n\n"
        f"_La oferta vence en {minutes_left} min._"
    )