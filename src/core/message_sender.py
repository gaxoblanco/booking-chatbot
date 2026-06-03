"""
MessageSender — Envíos WhatsApp centralizados con reintentos
=============================================================
Ubicación: src/core/message_sender.py

Centraliza TODOS los envíos salientes de WhatsApp del sistema.
Usa Meta Cloud API (Graph API) directamente — sin Twilio.

Reemplaza los bloques `client.messages.create()` dispersos en:
    - src/services/reminder_service.py      (_send_reminder)
    - src/services/waitlist_service.py      (_send_offer)
    - src/services/cancellation_notifier.py (_send_whatsapp)

Funcionalidades:
    1. Reintento automático hasta 3 veces con backoff (1, 5, 15 min)
    2. Detección de errores Meta: número inválido, no en WhatsApp, bloqueado
    3. Alerta al profesional después del tercer fallo
    4. Cola de reintentos persistida en BD (sobrevive reinicios)
    5. Procesamiento de cola desde el CRON diario

Variables de entorno requeridas:
    META_PHONE_NUMBER_ID  — ID del número en Meta (no el número en sí)
    META_WHATSAPP_TOKEN   — Token permanente de la app
    META_API_VERSION      — Versión de la API (ej: v22.0)

Uso en servicios:
    from src.core.message_sender import message_sender

    ok = message_sender.send_with_retry(
        to_phone           = client_phone,
        message            = texto,
        professional_phone = prof_phone,     # para la alerta de fallo
        patient_name       = nombre,         # para el mensaje de alerta
        appointment_id     = apt_id,         # para contexto en logs
    )
"""

import os
import logging
import requests as http_requests
from datetime import datetime, timedelta
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Códigos de error de Meta Cloud API relevantes
# Referencia: developers.facebook.com/docs/whatsapp/cloud-api/support/error-codes
META_ERROR_NO_WHATSAPP    = 131026  # Número no tiene WhatsApp activo
META_ERROR_INVALID_NUMBER = 131030  # Número de teléfono inválido
META_ERROR_UNSUBSCRIBED   = 131047  # Usuario bloqueó o está en opt-out

# Alias para compatibilidad con el resto del código que usa los nombres viejos
TWILIO_ERROR_NO_WHATSAPP   = META_ERROR_NO_WHATSAPP
TWILIO_ERROR_INVALID_NUMBER = META_ERROR_INVALID_NUMBER
TWILIO_ERROR_UNSUBSCRIBED   = META_ERROR_UNSUBSCRIBED


class MessageSender:
    """
    Servicio centralizado para envíos WhatsApp salientes.

    Todos los servicios que envían mensajes proactivos (recordatorios,
    ofertas de waitlist, notificaciones de cancelación) deben usar
    esta clase en lugar de llamar a Twilio directamente.
    """

    MAX_RETRIES     = 3
    BACKOFF_MINUTES = [1, 5, 15]   # minutos entre reintentos

    # =========================================================================
    # API PÚBLICA
    # =========================================================================

    def send_with_retry(
        self,
        to_phone:            str,
        message:             str,
        professional_phone:  Optional[str] = None,
        patient_name:        Optional[str] = None,
        appointment_id:      Optional[int] = None,
        content_sid:         Optional[str] = None,
        content_variables:   Optional[str] = None,
    ) -> bool:
        """
        Envía un WhatsApp con reintento automático en caso de fallo.

        En el primer intento, llama a Meta Cloud API directamente.
        Si falla, encola en `message_retry_queue` para reintentos
        posteriores (procesados por el CRON via process_retry_queue()).

        Si el error indica número sin WhatsApp o se agotan los 3 reintentos,
        envía una alerta al profesional.

        Args:
            to_phone:           Destinatario en formato E.164
            message:            Texto del mensaje
            professional_phone: Profesional a alertar si el envío falla
            patient_name:       Nombre del paciente (para el mensaje de alerta)
            appointment_id:     ID de la cita (para contexto en logs y BD)
            content_sid:        Nombre del template aprobado en Meta (opcional)
            content_variables:  JSON con variables del template (opcional)

        Returns:
            True si el mensaje fue aceptado por Meta
            False si falló (se habrá encolado para reintento)
        """
        logger.info(f"[MSG-SENDER] 📤 Enviando a {to_phone} (apt #{appointment_id})")

        success, error_code = self._send_meta(
            to_phone           = to_phone,
            message            = message,
            content_sid        = content_sid,
            content_variables  = content_variables,
        )

        if success:
            logger.info(f"[MSG-SENDER] ✅ Enviado correctamente a {to_phone}")
            return True

        # ── Fallo en el primer intento ────────────────────────────────────────

        # Error 63003 — el número no tiene WhatsApp: no tiene sentido reintentar
        if error_code in (TWILIO_ERROR_NO_WHATSAPP,
                          TWILIO_ERROR_INVALID_NUMBER,
                          TWILIO_ERROR_UNSUBSCRIBED):
            logger.warning(
                f"[MSG-SENDER] ⚠️ {to_phone} no tiene WhatsApp activo "
                f"(error {error_code}) — sin reintento"
            )
            self._alert_professional(
                professional_phone = professional_phone,
                patient_phone      = to_phone,
                patient_name       = patient_name,
                appointment_id     = appointment_id,
                error_code         = error_code,
            )
            return False

        # Otro error — encolar para reintento
        logger.warning(
            f"[MSG-SENDER] ⚠️ Fallo enviando a {to_phone} "
            f"(error {error_code}) — encolando para reintento"
        )
        self._enqueue(
            to_phone           = to_phone,
            message            = message,
            professional_phone = professional_phone,
            patient_name       = patient_name,
            appointment_id     = appointment_id,
            content_sid        = content_sid,
            content_variables  = content_variables,
        )
        return False

    def process_retry_queue(self) -> Dict:
        """
        Procesa los mensajes pendientes de reintento en la cola.

        Llamado desde el CRON diario como paso 0 (antes de los recordatorios).
        Lee los mensajes con `next_retry_at <= ahora` y los reintenta.

        Si un mensaje agota MAX_RETRIES, alerta al profesional y lo marca
        como `failed`.

        Returns:
            {
                'processed': int,   # mensajes procesados
                'sent':      int,   # enviados exitosamente
                'failed':    int,   # agotaron reintentos
                'skipped':   int,   # aún no es su momento
                'errors':    int,   # errores inesperados
            }
        """
        from src.database.database import db

        stats = {'processed': 0, 'sent': 0, 'failed': 0, 'skipped': 0, 'errors': 0}

        try:
            pending = self._get_pending_queue(db)
            stats['processed'] = len(pending)

            if not pending:
                logger.info("[MSG-SENDER] ✅ Cola de reintentos vacía")
                return stats

            logger.info(f"[MSG-SENDER] 🔄 Procesando {len(pending)} mensaje(s) en cola")

            for item in pending:
                try:
                    # ¿Ya llegó el momento de reintentar?
                    if item['next_retry_at']:
                        # SQLite retorna timestamps con espacio: "2026-03-22 17:30:00"
                        # fromisoformat en Python 3.10 requiere "T" como separador
                        ts_str     = str(item['next_retry_at']).replace(' ', 'T')
                        next_retry = datetime.fromisoformat(ts_str)
                        if next_retry > datetime.now():
                            stats['skipped'] += 1
                            continue

                    attempts = item['attempts'] + 1

                    success, error_code = self._send_meta(
                        to_phone          = item['to_phone'],
                        message           = item['message'],
                        content_sid       = item.get('content_sid'),
                        content_variables = item.get('content_variables'),
                    )

                    if success:
                        self._mark_queue_sent(db, item['id'])
                        stats['sent'] += 1
                        logger.info(
                            f"[MSG-SENDER] ✅ Reintento {attempts} exitoso "
                            f"para {item['to_phone']}"
                        )

                    elif attempts >= self.MAX_RETRIES:
                        # Agotó los reintentos
                        self._mark_queue_failed(db, item['id'])
                        self._alert_professional(
                            professional_phone = item.get('professional_phone'),
                            patient_phone      = item['to_phone'],
                            patient_name       = item.get('patient_name'),
                            appointment_id     = item.get('appointment_id'),
                            error_code         = error_code,
                        )
                        stats['failed'] += 1
                        logger.warning(
                            f"[MSG-SENDER] ❌ {item['to_phone']} agotó "
                            f"{self.MAX_RETRIES} reintentos — profesional alertado"
                        )

                    else:
                        # Programar siguiente reintento
                        backoff = self.BACKOFF_MINUTES[
                            min(attempts - 1, len(self.BACKOFF_MINUTES) - 1)
                        ]
                        self._update_queue_attempt(db, item['id'], attempts, backoff)
                        logger.info(
                            f"[MSG-SENDER] ⏳ Reintento {attempts} fallido para "
                            f"{item['to_phone']} — próximo en {backoff} min"
                        )

                except Exception as e:
                    logger.error(
                        f"[MSG-SENDER] ❌ Error procesando item #{item['id']}: {e}"
                    )
                    stats['errors'] += 1

        except Exception as e:
            logger.error(f"[MSG-SENDER] ❌ Error crítico en process_retry_queue: {e}")
            stats['errors'] += 1

        logger.info(f"[MSG-SENDER] 📊 Cola procesada: {stats}")
        return stats

    # =========================================================================
    # ENVÍO META CLOUD API
    # =========================================================================

    def _send_meta(
        self,
        to_phone:          str,
        message:           str,
        content_sid:       Optional[str] = None,
        content_variables: Optional[str] = None,
    ) -> tuple[bool, Optional[int]]:
        """
        Llama directamente a Meta Cloud API (Graph API) para enviar el mensaje.

        Soporta dos modos:
        - Template aprobado: content_sid = nombre del template + content_variables
                             (recordatorios, ofertas de waitlist)
        - Mensaje libre:     body directo (notificaciones, alertas)
                             Solo válido dentro de la ventana de 24hs de conversación.

        Endpoint:
            POST https://graph.facebook.com/{version}/{phone_number_id}/messages

        Returns:
            (True,  None)        si Meta aceptó el mensaje
            (False, error_code)  si Meta retornó error con código conocido
            (False, None)        si hubo excepción inesperada
        """
        try:
            token           = os.getenv('META_WHATSAPP_TOKEN', '').strip()
            phone_number_id = os.getenv('META_PHONE_NUMBER_ID', '').strip()
            api_version     = os.getenv('META_API_VERSION', 'v22.0').strip()

            if not all([token, phone_number_id]):
                logger.error(
                    "[MSG-SENDER] ❌ META_WHATSAPP_TOKEN o META_PHONE_NUMBER_ID "
                    "no configurados en .env"
                )
                return False, None

            # Meta espera el número sin '+' ni prefijos
            clean_phone = to_phone.replace('whatsapp:', '').replace('+', '').strip()

            url     = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type':  'application/json',
            }

            # ── Modo template ─────────────────────────────────────────────────
            if content_sid:
                # content_sid = nombre del template (ej: "recordatorio_turno")
                # content_variables = JSON con los parámetros, ej: '{"1":"lunes","2":"10:00"}'
                import json as _json
                try:
                    variables = _json.loads(content_variables or '{}')
                except Exception:
                    variables = {}

                # Convertir variables a formato de componentes de Meta
                # Meta espera una lista de parámetros, no un dict con keys "1", "2"...
                parameters = [
                    {'type': 'text', 'text': str(v)}
                    for v in variables.values()
                ]

                payload = {
                    'messaging_product': 'whatsapp',
                    'to':                clean_phone,
                    'type':              'template',
                    'template': {
                        'name':     content_sid,
                        'language': {'code': os.getenv('META_REMINDER_TEMPLATE_LANG', 'es_AR')},
                        'components': [{
                            'type':       'body',
                            'parameters': parameters,
                        }] if parameters else [],
                    }
                }

            # ── Modo mensaje libre ────────────────────────────────────────────
            else:
                payload = {
                    'messaging_product': 'whatsapp',
                    'to':                clean_phone,
                    'type':              'text',
                    'text':              {'body': message},
                }

            response = http_requests.post(url, headers=headers, json=payload, timeout=10)
            data     = response.json()

            # ── Interpretar respuesta ─────────────────────────────────────────
            if response.status_code == 200 and data.get('messages'):
                msg_id = data['messages'][0].get('id', '')
                logger.debug(f"[MSG-SENDER] Meta message_id: {msg_id}")
                return True, None

            # Error de Meta — extraer código para clasificar el fallo
            error      = data.get('error', {})
            error_code = error.get('code')
            error_msg  = error.get('message', 'error desconocido')

            logger.warning(
                f"[MSG-SENDER] ⚠️ Meta error {error_code}: {error_msg} "
                f"(HTTP {response.status_code}) → {to_phone}"
            )
            return False, error_code

        except Exception as e:
            logger.error(f"[MSG-SENDER] ❌ Error inesperado enviando a {to_phone}: {e}")
            return False, None

    def send_message(self, phone: str, message: str) -> bool:
        """
        Envío simple sin reintento — para respuestas inmediatas del bot.

        Usado por whatsapp_handler._send_reply() cuando el bot responde
        a un mensaje entrante. No se encola porque la ventana de 24hs
        garantiza que el mensaje libre es válido.

        Args:
            phone:   Número en formato E.164
            message: Texto a enviar

        Returns:
            True si Meta aceptó el mensaje
        """
        success, error_code = self._send_meta(to_phone=phone, message=message)
        if not success:
            logger.warning(
                f"[MSG-SENDER] ⚠️ send_message falló para {phone} "
                f"(error {error_code}) — sin reintento"
            )
        return success

    # =========================================================================
    # ALERTA AL PROFESIONAL
    # =========================================================================

    def _alert_professional(
        self,
        professional_phone: Optional[str],
        patient_phone:      str,
        patient_name:       Optional[str],
        appointment_id:     Optional[int],
        error_code:         Optional[int] = None,
    ):
        """
        Envía un WhatsApp al profesional informando que no se pudo
        contactar al paciente.

        No reintenta este envío — si el profesional tampoco tiene WhatsApp
        activo, el error se loggea y se descarta.

        Personaliza el mensaje según el tipo de error:
        - 63003: número sin WhatsApp activo
        - Otro:  fallo genérico de envío
        """
        if not professional_phone:
            logger.warning(
                "[MSG-SENDER] ⚠️ Sin professional_phone — "
                "no se puede alertar del fallo de envío"
            )
            return

        nombre = patient_name or patient_phone
        apt_info = f" (turno #{appointment_id})" if appointment_id else ""

        if error_code == TWILIO_ERROR_NO_WHATSAPP:
            mensaje = (
                f"⚠️ *Aviso del sistema*\n\n"
                f"El número *{patient_phone}* de *{nombre}*{apt_info} "
                f"no tiene WhatsApp activo.\n\n"
                f"El turno está cargado pero no pudimos notificarle. "
                f"Por favor coordiná directamente con el/la paciente."
            )
        else:
            mensaje = (
                f"⚠️ *Aviso del sistema*\n\n"
                f"No pudimos contactar a *{nombre}* ({patient_phone}){apt_info} "
                f"después de {self.MAX_RETRIES} intentos.\n\n"
                f"Por favor coordiná directamente con el/la paciente."
            )

        logger.info(
            f"[MSG-SENDER] 📲 Alertando a profesional {professional_phone} "
            f"sobre fallo con {patient_phone}"
        )

        # Envío directo sin reintento para evitar recursión
        success, _ = self._send_meta(
            to_phone = professional_phone,
            message  = mensaje,
        )

        if success:
            logger.info(f"[MSG-SENDER] ✅ Profesional {professional_phone} alertado")
        else:
            logger.error(
                f"[MSG-SENDER] ❌ No se pudo alertar al profesional "
                f"{professional_phone} — fallo crítico de comunicación"
            )

    # =========================================================================
    # COLA DE REINTENTOS — BD
    # =========================================================================

    def _enqueue(
        self,
        to_phone:           str,
        message:            str,
        professional_phone: Optional[str],
        patient_name:       Optional[str],
        appointment_id:     Optional[int],
        content_sid:        Optional[str],
        content_variables:  Optional[str],
    ):
        """Inserta un mensaje en la cola de reintentos."""
        try:
            from src.database.database import db

            # Primer reintento en BACKOFF_MINUTES[0] minutos
            next_retry = (
                datetime.now() + timedelta(minutes=self.BACKOFF_MINUTES[0])
            ).isoformat()

            with db.get_connection() as conn:
                conn.execute("""
                    INSERT INTO message_retry_queue
                        (to_phone, message, professional_phone, patient_name,
                         appointment_id, content_sid, content_variables,
                         attempts, next_retry_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, 'pending')
                """, (
                    to_phone, message, professional_phone, patient_name,
                    appointment_id, content_sid, content_variables,
                    next_retry,
                ))
            logger.info(
                f"[MSG-SENDER] 📋 Mensaje encolado para {to_phone} "
                f"— primer reintento en {self.BACKOFF_MINUTES[0]} min"
            )
        except Exception as e:
            logger.error(f"[MSG-SENDER] ❌ Error encolando mensaje: {e}")

    def _get_pending_queue(self, db) -> list:
        """Retorna mensajes pendientes cuyo momento de reintento ya llegó."""
        try:
            with db.get_connection() as conn:
                rows = conn.execute("""
                    SELECT *
                    FROM message_retry_queue
                    WHERE status = 'pending'
                      AND attempts < ?
                    ORDER BY next_retry_at ASC
                """, (self.MAX_RETRIES,)).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"[MSG-SENDER] ❌ Error leyendo cola: {e}")
            return []

    def _mark_queue_sent(self, db, queue_id: int):
        """Marca un ítem de la cola como enviado exitosamente."""
        try:
            with db.get_connection() as conn:
                conn.execute("""
                    UPDATE message_retry_queue
                    SET status = 'sent', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (queue_id,))
        except Exception as e:
            logger.error(f"[MSG-SENDER] ❌ Error marcando enviado #{queue_id}: {e}")

    def _mark_queue_failed(self, db, queue_id: int):
        """Marca un ítem como fallido (agotó reintentos)."""
        try:
            with db.get_connection() as conn:
                conn.execute("""
                    UPDATE message_retry_queue
                    SET status = 'failed', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (queue_id,))
        except Exception as e:
            logger.error(f"[MSG-SENDER] ❌ Error marcando fallido #{queue_id}: {e}")

    def _update_queue_attempt(self, db, queue_id: int, attempts: int, backoff_min: int):
        """Actualiza el contador de intentos y programa el próximo reintento."""
        try:
            next_retry = (
                datetime.now() + timedelta(minutes=backoff_min)
            ).isoformat()
            with db.get_connection() as conn:
                conn.execute("""
                    UPDATE message_retry_queue
                    SET attempts       = ?,
                        next_retry_at  = ?,
                        updated_at     = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (attempts, next_retry, queue_id))
        except Exception as e:
            logger.error(f"[MSG-SENDER] ❌ Error actualizando intento #{queue_id}: {e}")


# Instancia global
message_sender = MessageSender()