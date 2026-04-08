"""
Event Store
===========
Ubicación: src/integrations/conversation_context_service/event_store.py

Capa de acceso a datos para la tabla conversation_events.
Responsabilidad única: leer y escribir eventos — sin lógica de inferencia.

La lógica de qué significa un evento (inferencia de contexto)
vive en context_service.py, no acá.

Política de retención:
    Los eventos se purgan automáticamente después de RETENTION_DAYS días.
    El job diario en engine.py llama a purge_old_events().
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from src.database.database import db

logger = logging.getLogger(__name__)

# Días de retención de eventos — configurable acá, no en .env
# (no es algo que el operador necesite cambiar en producción)
RETENTION_DAYS = 7


class EventStore:
    """
    Escritura y lectura de conversation_events.
    Stateless — cada llamada abre y cierra su conexión.
    """

    # =========================================================================
    # ESCRITURA
    # =========================================================================

    def record(
        self,
        client_phone: str,
        event_type: str,
        session_id: Optional[str] = None,
        intent: Optional[str] = None,
        confidence: Optional[float] = None,
        state_before: Optional[str] = None,
        state_after: Optional[str] = None,
        appointment_id: Optional[int] = None,
    ) -> Optional[int]:
        """
        Inserta un evento de conversación.

        Args:
            client_phone:   Teléfono del cliente (sin anonimizar — necesario para lookup).
            event_type:     Tipo de evento. Valores válidos:
                            'message' | 'reminder_sent' | 'reminder_response' |
                            'booking' | 'cancel' | 'reschedule' | 'flow_interrupted'
            session_id:     ID de sesión Redis para agrupar turnos de una misma conversación.
            intent:         Intent detectado por el NLU (ej: 'search_professional').
            confidence:     Confianza del NLU (0.0 - 1.0).
            state_before:   Estado de sesión antes del mensaje.
            state_after:    Estado de sesión después del mensaje.
            appointment_id: ID de cita relacionada (opcional).

        Returns:
            ID del evento insertado, o None si falló.
        """
        try:
            with db.get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO conversation_events
                        (client_phone, session_id, event_type, intent, confidence,
                         state_before, state_after, appointment_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    client_phone,
                    session_id,
                    event_type,
                    intent,
                    round(confidence, 3) if confidence is not None else None,
                    state_before,
                    state_after,
                    appointment_id,
                ))
                event_id = cursor.lastrowid
                logger.debug(
                    f"[EVENT_STORE] #{event_id} — {client_phone} "
                    f"| {event_type} | intent={intent}"
                )
                return event_id
        except Exception as e:
            logger.error(f"[EVENT_STORE] Error guardando evento para {client_phone}: {e}")
            return None

    # =========================================================================
    # LECTURA
    # =========================================================================

    def get_recent(
        self,
        client_phone: str,
        window_minutes: int = 180,
        limit: int = 20,
    ) -> list[dict]:
        """
        Retorna los eventos recientes de un cliente dentro de una ventana de tiempo.

        Args:
            client_phone:   Teléfono del cliente.
            window_minutes: Ventana hacia atrás en minutos (default: 3 horas).
            limit:          Máximo de eventos a retornar.

        Returns:
            Lista de dicts ordenada por created_at ASC (más antiguo primero).
            Lista vacía si no hay eventos o falla la consulta.
        """
        try:
            since = datetime.now() - timedelta(minutes=window_minutes)
            with db.get_connection() as conn:
                rows = conn.execute("""
                    SELECT id, client_phone, session_id, event_type,
                           intent, confidence, state_before, state_after,
                           appointment_id, created_at
                    FROM conversation_events
                    WHERE client_phone = ?
                      AND created_at >= ?
                    ORDER BY created_at ASC
                    LIMIT ?
                """, (client_phone, since.isoformat(), limit)).fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"[EVENT_STORE] Error leyendo eventos de {client_phone}: {e}")
            return []

    def get_last_event(
        self,
        client_phone: str,
        event_type: Optional[str] = None,
        window_minutes: int = 180,
    ) -> Optional[dict]:
        """
        Retorna el evento más reciente de un cliente, opcionalmente filtrado por tipo.

        Útil para preguntas del tipo:
            "¿Cuál fue el último intent de este usuario en las últimas 3 horas?"
            "¿Hubo un reminder_sent reciente?"

        Args:
            client_phone:   Teléfono del cliente.
            event_type:     Filtrar por tipo (opcional).
            window_minutes: Ventana hacia atrás en minutos.

        Returns:
            Dict con el evento, o None si no hay.
        """
        try:
            since = datetime.now() - timedelta(minutes=window_minutes)
            query = """
                SELECT id, client_phone, session_id, event_type,
                       intent, confidence, state_before, state_after,
                       appointment_id, created_at
                FROM conversation_events
                WHERE client_phone = ?
                  AND created_at >= ?
            """
            params = [client_phone, since.isoformat()]

            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)

            query += " ORDER BY created_at DESC LIMIT 1"

            with db.get_connection() as conn:
                row = conn.execute(query, params).fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"[EVENT_STORE] Error en get_last_event para {client_phone}: {e}")
            return None

    # =========================================================================
    # PURGA
    # =========================================================================

    def purge_old_events(self) -> int:
        """
        Elimina eventos más antiguos que RETENTION_DAYS días.
        Llamado por el job diario en engine.py.

        Returns:
            Cantidad de filas eliminadas.
        """
        try:
            cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
            with db.get_connection() as conn:
                cursor = conn.execute("""
                    DELETE FROM conversation_events
                    WHERE created_at < ?
                """, (cutoff.isoformat(),))
                deleted = cursor.rowcount
                if deleted > 0:
                    logger.info(f"[EVENT_STORE] Purga: {deleted} eventos eliminados (>{RETENTION_DAYS}d)")
                return deleted
        except Exception as e:
            logger.error(f"[EVENT_STORE] Error en purga: {e}")
            return 0


# Instancia global
event_store = EventStore()
