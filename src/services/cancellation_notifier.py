"""
CancellationNotifier
====================
Ubicación: src/services/cancellation_notifier.py

Notifica al paciente cuando el profesional cancela un turno
desde Google Calendar.

Flujo completo:
    1. Recibe el appointment_id de una cita cancelada
    2. Valida que no fue notificada antes (cancellation_notified)
    3. Obtiene los datos del turno y del profesional
    4. Busca el próximo slot disponible del mismo profesional
    5. Formatea el mensaje con fecha cancelada + próxima disponibilidad
    6. Envía WhatsApp al paciente via Twilio
    7. Marca cancellation_notified = 1 en BD (evita doble envío)

Llamado desde:
    - src/api/whatsapp_handler.py → _process_calendar_change()
      (disparado por push notification de Google Calendar)
    - src/cron/daily_reminder_job.py
      (fallback si el webhook no llegó — sync periódico)
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class CancellationNotifier:
    """
    Servicio que notifica al paciente cuando el profesional
    cancela su turno desde Google Calendar.
    """

    # Días hacia adelante en que busca el próximo slot disponible
    NEXT_SLOT_SEARCH_DAYS = 14

    def __init__(self):
        # Imports lazy para evitar circulares al inicio del proceso
        from src.database.database import db
        self.db = db

    # =========================================================================
    # MÉTODO PRINCIPAL
    # =========================================================================

    def notify_patient(self, appointment_id: int) -> Dict:
        """
        Notifica al paciente que su turno fue cancelado y le ofrece
        el próximo slot disponible del mismo profesional.

        Args:
            appointment_id: ID del turno cancelado en BD

        Returns:
            {
                'success': bool,
                'action':  str,   # 'notified' | 'already_notified' | 'no_phone' | 'error'
                'error':   str    # solo si success=False
            }
        """
        logger.info(
            f"[NOTIFIER] 🔔 Procesando notificación para cita #{appointment_id}"
        )

        try:
            # ── 1. Obtener datos del turno ────────────────────────────────────
            apt = self.db.get_appointment(appointment_id)

            if not apt:
                logger.warning(
                    f"[NOTIFIER] ⚠️ Cita #{appointment_id} no encontrada en BD"
                )
                return {'success': False, 'action': 'error',
                        'error': 'appointment_not_found'}

            # ── 2. Validar que realmente fue cancelada por el profesional ─────
            if apt.get('status') != 'cancelada_profesional':
                logger.info(
                    f"[NOTIFIER] ℹ️ Cita #{appointment_id} no está cancelada "
                    f"por profesional (status: {apt.get('status')}) — ignorada"
                )
                return {'success': False, 'action': 'error',
                        'error': 'not_cancelled_by_professional'}

            # ── 3. Verificar que no fue notificada antes ──────────────────────
            if apt.get('cancellation_notified'):
                logger.info(
                    f"[NOTIFIER] ℹ️ Cita #{appointment_id} ya fue notificada — skip"
                )
                return {'success': True, 'action': 'already_notified'}

            # ── 4. Verificar que el paciente tiene número ─────────────────────
            client_phone = apt.get('client_phone', '').strip()
            if not client_phone:
                logger.warning(
                    f"[NOTIFIER] ⚠️ Cita #{appointment_id} sin client_phone — "
                    f"no se puede notificar"
                )
                self._mark_notified(appointment_id)  # Marcar para no reintentar
                return {'success': False, 'action': 'no_phone',
                        'error': 'no_client_phone'}

            # ── 5. Buscar próximo slot del mismo profesional ──────────────────
            next_slot = self._find_next_slot(
                professional_phone  = apt['professional_phone'],
                from_date           = apt['appointment_date'],
            )

            # ── 6. Formatear y enviar el mensaje ─────────────────────────────
            message = self._format_message(apt, next_slot)
            sent    = self._send_whatsapp(client_phone, message)

            if not sent:
                logger.error(
                    f"[NOTIFIER] ❌ Falló el envío a {client_phone} "
                    f"para cita #{appointment_id}"
                )
                return {'success': False, 'action': 'error',
                        'error': 'whatsapp_send_failed'}

            # ── 7. Marcar como notificada en BD ──────────────────────────────
            self._mark_notified(appointment_id)

            logger.info(
                f"[NOTIFIER] ✅ Paciente notificado — cita #{appointment_id} "
                f"→ {client_phone}"
            )
            return {'success': True, 'action': 'notified'}

        except Exception as e:
            logger.error(
                f"[NOTIFIER] ❌ Error inesperado en notify_patient "
                f"para cita #{appointment_id}: {e}"
            )
            import traceback
            traceback.print_exc()
            return {'success': False, 'action': 'error', 'error': str(e)}

    # =========================================================================
    # BÚSQUEDA DEL PRÓXIMO SLOT
    # =========================================================================

    def _find_next_slot(
        self,
        professional_phone: str,
        from_date: str,
    ) -> Optional[Dict]:
        """
        Busca el próximo slot disponible del profesional a partir de
        la fecha del turno cancelado (sin incluirla).

        Usa professional_service.get_available_slots() que ya maneja
        working_hours, slot_duration, cache y Google Calendar.

        Args:
            professional_phone: Teléfono del profesional
            from_date:          Fecha del turno cancelado (YYYY-MM-DD)
                                La búsqueda empieza al día siguiente.

        Returns:
            Dict con el primer slot encontrado:
            {
                'date':  'YYYY-MM-DD',
                'start': 'HH:MM',
                'end':   'HH:MM',
            }
            None si no hay disponibilidad en los próximos NEXT_SLOT_SEARCH_DAYS días.
        """
        from src.services.professional_service import professional_service
        from datetime import datetime, timedelta

        # Empezar a buscar desde el día SIGUIENTE al cancelado
        try:
            start = datetime.strptime(from_date, '%Y-%m-%d') + timedelta(days=1)
        except ValueError:
            start = datetime.now() + timedelta(days=1)

        logger.info(
            f"[NOTIFIER] 🔍 Buscando próximo slot de {professional_phone} "
            f"desde {start.strftime('%Y-%m-%d')} "
            f"(máx {self.NEXT_SLOT_SEARCH_DAYS} días)"
        )

        for day_offset in range(self.NEXT_SLOT_SEARCH_DAYS):
            check_date = (start + timedelta(days=day_offset)).strftime('%Y-%m-%d')

            try:
                slots = professional_service.get_available_slots(
                    professional_phone = professional_phone,
                    date               = check_date,
                )
                if slots:
                    first = slots[0]
                    logger.info(
                        f"[NOTIFIER] ✅ Próximo slot encontrado: "
                        f"{check_date} {first.get('start', '')} - {first.get('end', '')}"
                    )
                    return {
                        'date':  check_date,
                        'start': first.get('start', ''),
                        'end':   first.get('end', ''),
                    }

            except Exception as e:
                logger.warning(
                    f"[NOTIFIER] ⚠️ Error buscando slots en {check_date}: {e}"
                )
                continue

        logger.info(
            f"[NOTIFIER] ℹ️ Sin disponibilidad en los próximos "
            f"{self.NEXT_SLOT_SEARCH_DAYS} días para {professional_phone}"
        )
        return None

    # =========================================================================
    # FORMATO DEL MENSAJE
    # =========================================================================

    def _format_message(self, apt: Dict, next_slot: Optional[Dict]) -> str:
        """
        Formatea el mensaje de WhatsApp que recibe el paciente.

        Incluye:
        - Qué turno fue cancelado (profesional, fecha, hora)
        - Si hay próxima disponibilidad → la ofrece con instrucción de respuesta
        - Si no hay → invita a consultar disponibilidad

        Args:
            apt:       Datos del turno cancelado (del get_appointment())
            next_slot: Próximo slot disponible o None

        Returns:
            Texto formateado listo para enviar por WhatsApp
        """
        from src.config.domain_config import DomainConfig

        # Datos del turno cancelado
        prof_name        = apt.get('professional_name', 'tu profesional')
        appointment_name = getattr(DomainConfig, 'APPOINTMENT_NAME', 'turno')
        client_name      = apt.get('client_name', '').split()[0] if apt.get('client_name') else ''

        # Formatear fecha cancelada
        try:
            date_obj     = datetime.strptime(apt['appointment_date'], '%Y-%m-%d')
            dias         = ['Lunes', 'Martes', 'Miércoles', 'Jueves',
                            'Viernes', 'Sábado', 'Domingo']
            dia_nombre   = dias[date_obj.weekday()]
            fecha_cancel = f"{dia_nombre} {date_obj.strftime('%d/%m/%Y')}"
        except Exception:
            fecha_cancel = apt.get('appointment_date', 'fecha desconocida')

        hora_cancel = apt.get('start', '')

        # Saludo personalizado si tenemos el nombre
        saludo = f"Hola {client_name}!" if client_name else "Hola!"

        # Bloque base: info del turno cancelado
        mensaje = (
            f"{saludo}\n\n"
            f"⚠️ *Tu {appointment_name} fue cancelado*\n\n"
            f"👨‍⚕️ *Profesional:* {prof_name}\n"
            f"📅 *Fecha:* {fecha_cancel}\n"
            f"⏰ *Horario:* {hora_cancel} hs\n\n"
            f"Lamentamos los inconvenientes."
        )

        # Bloque de próxima disponibilidad
        if next_slot:
            try:
                next_date_obj  = datetime.strptime(next_slot['date'], '%Y-%m-%d')
                next_dia       = dias[next_date_obj.weekday()]
                next_fecha_str = f"{next_dia} {next_date_obj.strftime('%d/%m/%Y')}"
            except Exception:
                next_fecha_str = next_slot.get('date', '')

            next_hora = next_slot.get('start', '')

            mensaje += (
                f"\n\n📅 *Próxima disponibilidad:*\n"
                f"{next_fecha_str} a las {next_hora} hs\n\n"
                f"¿Querés que te agendemos en ese horario?\n\n"
                f"1️⃣ Sí, agendame\n"
                f"2️⃣ No, prefiero elegir otro horario"
            )
        else:
            mensaje += (
                f"\n\nPor el momento {prof_name} no tiene disponibilidad "
                f"en los próximos días.\n\n"
                f"Escribí *buscar* cuando quieras consultar nuevos horarios."
            )

        return mensaje

    # =========================================================================
    # ENVÍO POR WHATSAPP
    # =========================================================================

    def _send_whatsapp(self, to_phone: str, message: str) -> bool:
        """Envía WhatsApp vía MessageSender centralizado."""
        from src.core.message_sender import message_sender
        return message_sender.send_with_retry(
            to_phone = to_phone,
            message  = message,
        )

    # =========================================================================
    # PERSISTENCIA
    # =========================================================================

    def _mark_notified(self, appointment_id: int):
        """
        Marca la cita como notificada en BD.

        Impide que el sistema envíe el mensaje dos veces si:
        - El CRON y el webhook corren en paralelo
        - El webhook llega con delay después del CRON

        Args:
            appointment_id: ID del turno en BD
        """
        try:
            with self.db.get_connection() as conn:
                conn.execute("""
                    UPDATE appointments
                    SET cancellation_notified = 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (appointment_id,))

            logger.debug(
                f"[NOTIFIER] ✅ Cita #{appointment_id} marcada como notificada"
            )
        except Exception as e:
            logger.error(
                f"[NOTIFIER] ❌ Error marcando cita #{appointment_id} "
                f"como notificada: {e}"
            )


# Instancia global — importar así en otros módulos:
#   from src.services.cancellation_notifier import cancellation_notifier
cancellation_notifier = CancellationNotifier()
