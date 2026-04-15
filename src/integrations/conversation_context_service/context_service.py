"""
Context Service
===============
Ubicación: src/integrations/conversation_context_service/context_service.py

Responde preguntas de alto nivel sobre el contexto de un usuario
usando los eventos persistidos en conversation_events.

Responsabilidad: INFERIR — no escribe en BD, solo lee via event_store.

Preguntas que responde:
    - ¿Tiene este usuario un recordatorio pendiente de respuesta?
    - ¿Estaba en medio de un flujo que abandonó?
    - ¿Qué fue lo último que hizo en las últimas N horas?

Quién lo usa:
    - bot_controller → antes del NLU para orientar el routing
    - should_handle_as_reminder → señal adicional de contexto
    - (futuro) context_service.get_interrupted_flow() para retomar conversaciones
"""

import logging
import os
from datetime import datetime
from typing import Optional

from src.integrations.conversation_context_service.event_store import event_store

logger = logging.getLogger(__name__)


# Estados que indican un flujo activo — si el último estado es uno de estos
# y la sesión expiró, el usuario estaba en medio de algo
_ACTIVE_FLOW_STATES = {
    # Búsqueda
    "client_multifilter_menu",
    "client_filter_input",
    "client_show_results",
    "client_view_detail",
    "client_view_detail_with_booking",

    # Reserva
    "client_confirm_booking",
    "client_collect_own_name",
    "client_third_party_choice",
    "client_third_party_name",
    "client_third_party_phone",
    "client_third_party_age",

    # Cancelación
    "client_cancel_appointment",
    "client_cancel_reason",
    "client_confirm_cancel",
    "client_select_cancel",

    # Reprogramación
    "client_reschedule_appointment",
    "client_reschedule_select_date",
    "client_reschedule_select_time",
    "client_reschedule_confirm",

    # Recordatorio
    "awaiting_reminder_response",
}

# Estados neutros — el usuario no estaba en medio de nada
_NEUTRAL_STATES = {
    "start",
    "client_main_menu",
    "client_new_user_menu",
    "client_booking_confirmed",
    "client_cancel_success",
}


def _parse_reminder_window() -> tuple[int, int]:
    """
    Lee REMINDER_SEND_TIME y REMINDER_CLOSE_TIME del .env.
    Retorna (open_minutes, close_minutes) desde medianoche.
    """
    def _to_min(var: str, default: str) -> int:
        raw = os.getenv(var, default)
        try:
            h, m = raw.split(":")
            return int(h) * 60 + int(m)
        except Exception:
            h, m = default.split(":")
            return int(h) * 60 + int(m)

    return (
        _to_min("REMINDER_SEND_TIME",  "17:30"),
        _to_min("REMINDER_CLOSE_TIME", "20:30"),
    )


class ContextService:
    """
    Inferencia de contexto conversacional entre sesiones.
    Solo lectura — no modifica BD.
    """

    # =========================================================================
    # API PRINCIPAL
    # =========================================================================

    def get_recent_context(
        self,
        client_phone: str,
        window_minutes: int = 180,
    ) -> dict:
        """
        Retorna un resumen del contexto reciente del usuario.

        Útil al inicio de una sesión nueva para orientar el routing
        sin depender del estado de Redis (que puede haber expirado).

        Args:
            client_phone:   Teléfono del cliente.
            window_minutes: Ventana hacia atrás (default: 3 horas = franja de recordatorio).

        Returns:
            {
                'has_recent_activity': bool,   — hubo actividad en la ventana
                'last_event_type': str | None, — tipo del último evento
                'last_intent': str | None,     — último intent detectado
                'last_state': str | None,      — último state_after registrado
                'pending_reminder': bool,      — hay reminder_sent en la ventana sin respuesta
                'interrupted_flow': str | None — flujo activo que quedó sin terminar
                'minutes_since_last': int | None — minutos desde el último evento
            }
        """
        events = event_store.get_recent(
            client_phone=client_phone,
            window_minutes=window_minutes,
        )

        if not events:
            return self._empty_context()

        last = events[-1]
        minutes_since = self._minutes_ago(last['created_at'])

        # Detectar si hay reminder pendiente sin respuesta en la ventana
        pending_reminder = self._has_pending_reminder(events, client_phone)

        # Detectar flujo interrumpido
        interrupted = self._detect_interrupted_flow(events)

        ctx = {
            'has_recent_activity': True,
            'last_event_type':     last['event_type'],
            'last_intent':         last['intent'],
            'last_state':          last['state_after'],
            'pending_reminder':    pending_reminder,
            'interrupted_flow':    interrupted,
            'minutes_since_last':  minutes_since,
        }

        logger.debug(
            f"[CTX] {client_phone} — last={last['event_type']} "
            f"({minutes_since}min) | reminder={pending_reminder} | "
            f"interrupted={interrupted}"
        )

        return ctx

    def had_reminder_sent(
        self,
        client_phone: str,
        window_minutes: Optional[int] = None,
    ) -> bool:
        """
        Indica si se envió un recordatorio al usuario dentro de la ventana horaria.

        Si window_minutes es None, usa la ventana configurada en .env
        (REMINDER_SEND_TIME → REMINDER_CLOSE_TIME).

        Úsalo como señal adicional en should_handle_as_reminder() para
        aumentar la certeza antes de interceptar el mensaje.

        Args:
            client_phone:   Teléfono del cliente.
            window_minutes: Minutos hacia atrás. None = ventana del .env.

        Returns:
            True si hubo un reminder_sent sin respuesta posterior.
        """
        if window_minutes is None:
            open_min, close_min = _parse_reminder_window()
            now_min = datetime.now().hour * 60 + datetime.now().minute
            # Si estamos dentro de la franja, la ventana es desde el inicio de la franja
            if open_min <= now_min <= close_min:
                window_minutes = now_min - open_min + 5  # +5 min de margen
            else:
                return False  # Fuera de franja → no hay reminder activo

        last_reminder = event_store.get_last_event(
            client_phone=client_phone,
            event_type='reminder_sent',
            window_minutes=window_minutes,
        )

        if not last_reminder:
            return False

        # Verificar que no haya una respuesta posterior
        last_response = event_store.get_last_event(
            client_phone=client_phone,
            event_type='reminder_response',
            window_minutes=window_minutes,
        )

        if not last_response:
            return True  # Reminder enviado, sin respuesta

        # Comparar timestamps: si la respuesta es posterior al reminder, ya respondió
        reminder_ts = last_reminder['created_at']
        response_ts = last_response['created_at']
        return response_ts < reminder_ts  # True solo si la respuesta es más vieja

    def get_interrupted_flow(self, client_phone: str) -> Optional[str]:
        """
        Retorna el nombre del flujo que el usuario dejó sin terminar
        en la última sesión, o None si no hay flujo interrumpido.

        Valores posibles: 'booking' | 'cancel' | 'reschedule' | 'search' | None

        Args:
            client_phone: Teléfono del cliente.

        Returns:
            Nombre del flujo o None.
        """
        events = event_store.get_recent(client_phone=client_phone)
        return self._detect_interrupted_flow(events)

    # =========================================================================
    # HELPERS PRIVADOS
    # =========================================================================

    def _empty_context(self) -> dict:
        return {
            'has_recent_activity': False,
            'last_event_type':     None,
            'last_intent':         None,
            'last_state':          None,
            'pending_reminder':    False,
            'interrupted_flow':    None,
            'minutes_since_last':  None,
        }

    def _has_pending_reminder(self, events: list[dict], client_phone: str = None) -> bool:
        """
        Hay pending_reminder si existe un registro en appointment_reminders
        con status='sent' y la cita es futura.
        Fuente de verdad: BD directa — no conversation_events.
        """
        if not client_phone:
            return False
        try:
            from src.database.database import db
            with db.get_connection() as conn:
                row = conn.execute("""
                    SELECT COUNT(*) as cnt
                    FROM appointment_reminders r
                    JOIN appointments a ON r.appointment_id = a.id
                    WHERE r.client_phone = ?
                    AND r.status = 'sent'
                    AND a.appointment_date >= DATE('now')
                """, (client_phone,)).fetchone()
                return row['cnt'] > 0
        except Exception:
            return False

    def _detect_interrupted_flow(self, events: list[dict]) -> Optional[str]:
        """
        Analiza el último state_after registrado.
        Si es un estado de flujo activo, el usuario dejó algo sin terminar.
        """
        # Buscar el último evento con state_after registrado
        for e in reversed(events):
            state = e.get('state_after')
            if not state:
                continue

            if state in _NEUTRAL_STATES or state not in _ACTIVE_FLOW_STATES:
                return None  # Terminó en estado neutro o desconocido

            # Mapear estado → nombre de flujo
            if 'booking' in state or 'confirm_booking' in state or 'third_party' in state:
                return 'booking'
            if 'cancel' in state:
                return 'cancel'
            if 'reschedule' in state:
                return 'reschedule'
            if any(k in state for k in ['search', 'multifilter', 'filter', 'results', 'detail']):
                return 'search'
            if 'reminder' in state:
                return 'reminder'

        return None

    def _minutes_ago(self, timestamp_str: str) -> Optional[int]:
        """Convierte timestamp ISO a minutos desde ahora."""
        try:
            ts = datetime.fromisoformat(timestamp_str)
            delta = datetime.now() - ts
            return int(delta.total_seconds() / 60)
        except Exception:
            return None


# Instancia global
context_service = ContextService()
