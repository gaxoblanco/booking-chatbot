"""
WatchManager — Gestión de Push Notifications de Google Calendar
================================================================

Google Calendar permite recibir notificaciones en tiempo real (push)
cuando un calendario cambia. Este módulo gestiona el ciclo de vida
completo de esos "watch channels":

    1. create_watch()  — suscribirse a cambios de un calendario
    2. renew_watch()   — renovar antes del vencimiento (cada 6 días via CRON)
    3. stop_watch()    — cancelar suscripción (baja de profesional)
    4. renew_all_expiring() — renovación masiva (llamada desde CRON)

Cómo funciona:
    - La Service Account llama a events().watch() en Google Calendar API
    - Google registra un canal y comienza a hacer POST a nuestra URL
    - Cada POST llega a src/api/google_calendar_webhook.py
    - El canal expira cada 7 días → hay que renovarlo antes

Tabla en BD: calendar_watches
    professional_phone | calendar_id | channel_id | resource_id | expires_at

Author: Bot de Turnos
"""

import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List

from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class WatchManager:
    """
    Gestiona el ciclo de vida de los watch channels de Google Calendar.

    Cada profesional activo tiene exactamente UN watch channel activo
    por calendario. El manager se encarga de crearlos, renovarlos
    y detenerlos de forma segura.
    """

    # Google Calendar API: los watches expiran como máximo en 7 días.
    # Renovamos a los 6 días para tener 24hs de margen.
    WATCH_TTL_DAYS    = 7
    RENEW_BEFORE_DAYS = 1   # Renovar cuando falte 1 día para vencer

    def __init__(self, calendar_service, db, webhook_url: str):
        """
        Args:
            calendar_service: Instancia de GoogleCalendarService (ya autenticada)
            db:               Instancia de Database
            webhook_url:      URL pública donde Google hará POST
                              Ej: 'https://mi-dominio.com/google-calendar/webhook'
                              DEBE ser HTTPS y accesible desde internet
        """
        self.calendar_service = calendar_service
        self.db               = db
        self.webhook_url      = webhook_url

    # =========================================================================
    # CREAR WATCH
    # =========================================================================

    def create_watch(
        self,
        professional_phone: str,
        calendar_id: str
    ) -> Optional[Dict]:
        """
        Suscribe un calendario a notificaciones push de Google.

        Si ya existe un watch activo para ese calendario, lo detiene
        primero y crea uno nuevo (Google no permite duplicados).

        Args:
            professional_phone: Teléfono del profesional (para BD)
            calendar_id:        ID del calendario en Google (email del prof)

        Returns:
            Dict con datos del watch creado:
            {
                'channel_id':  str,   # UUID generado
                'resource_id': str,   # ID del recurso en Google
                'expires_at':  str,   # ISO datetime de vencimiento
            }
            None si hubo un error.
        """
        logger.info(
            f"[WATCH] Creando watch para {professional_phone} "
            f"(calendar: {calendar_id})"
        )

        # Si hay un watch activo, detenerlo antes de crear uno nuevo
        existing = self._get_active_watch(professional_phone)
        if existing:
            logger.info(
                f"[WATCH] Watch existente encontrado (#{existing['id']}), "
                f"deteniendo antes de crear nuevo"
            )
            self._stop_watch_in_google(existing['channel_id'], existing['resource_id'])
            self._mark_watch_stopped(existing['id'])

        # Generar un channel_id único — Google lo usa para identificar el canal
        channel_id = str(uuid.uuid4())

        # Token secreto que Google reenvía en cada notificación
        # Permite verificar que el POST realmente viene de Google
        channel_token = str(uuid.uuid4()).replace('-', '')

        # Calcular expiración: ahora + 7 días en milisegundos (formato Google)
        expires_dt     = datetime.now(timezone.utc) + timedelta(days=self.WATCH_TTL_DAYS)
        expires_ms     = int(expires_dt.timestamp() * 1000)  # Google usa ms
        expires_iso    = expires_dt.isoformat()

        body = {
            'id':      channel_id,
            'type':    'web_hook',
            'address': self.webhook_url,
            'token':   channel_token,
            'expiration': expires_ms,
        }

        try:
            # Llamar a Google Calendar API: events().watch()
            service     = self.calendar_service.calendar_client.service
            response    = service.events().watch(
                calendarId=calendar_id,
                body=body
            ).execute()

            resource_id = response.get('resourceId', '')

            logger.info(
                f"[WATCH] ✅ Watch creado — channel: {channel_id}, "
                f"resource: {resource_id}, vence: {expires_iso}"
            )

            # Persistir en BD
            watch_id = self._save_watch(
                professional_phone = professional_phone,
                calendar_id        = calendar_id,
                channel_id         = channel_id,
                resource_id        = resource_id,
                channel_token      = channel_token,
                expires_at         = expires_iso,
            )

            return {
                'watch_id':    watch_id,
                'channel_id':  channel_id,
                'resource_id': resource_id,
                'expires_at':  expires_iso,
            }

        except HttpError as e:
            # Error 400: webhook_url inválida o no HTTPS
            # Error 403: Service Account sin permisos en el calendario
            logger.error(
                f"[WATCH] ❌ Error HTTP creando watch para {calendar_id}: "
                f"status={e.resp.status}, detail={e}"
            )
            return None

        except Exception as e:
            logger.error(f"[WATCH] ❌ Error inesperado creando watch: {e}")
            import traceback
            traceback.print_exc()
            return None

    # =========================================================================
    # RENOVAR WATCH
    # =========================================================================

    def renew_watch(self, watch_id: int) -> Optional[Dict]:
        """
        Renueva un watch channel antes de que venza.

        Google no tiene endpoint de renovación — la renovación es
        detener el canal actual y crear uno nuevo.

        Args:
            watch_id: ID del watch en nuestra BD

        Returns:
            Dict con los datos del nuevo watch, o None si hubo error.
        """
        watch = self._get_watch_by_id(watch_id)
        if not watch:
            logger.warning(f"[WATCH] Watch #{watch_id} no encontrado en BD")
            return None

        logger.info(
            f"[WATCH] Renovando watch #{watch_id} "
            f"para {watch['professional_phone']}"
        )

        return self.create_watch(
            professional_phone = watch['professional_phone'],
            calendar_id        = watch['calendar_id'],
        )

    def renew_all_expiring(self) -> Dict:
        """
        Renueva todos los watches que vencen en las próximas 24 horas.

        Llamado desde el CRON diario (daily_reminder_job.py).

        Returns:
            {
                'checked':  int,   # total de watches activos
                'renewed':  int,   # renovados exitosamente
                'errors':   int,   # fallos
            }
        """
        stats = {'checked': 0, 'renewed': 0, 'errors': 0}

        try:
            expiring = self._get_expiring_watches()
            stats['checked'] = len(expiring)

            if not expiring:
                logger.info("[WATCH] ✅ No hay watches por vencer")
                return stats

            logger.info(f"[WATCH] 🔄 Renovando {len(expiring)} watches por vencer")

            for watch in expiring:
                result = self.renew_watch(watch['id'])
                if result:
                    stats['renewed'] += 1
                    logger.info(
                        f"[WATCH] ✅ Watch renovado para "
                        f"{watch['professional_phone']}"
                    )
                else:
                    stats['errors'] += 1
                    logger.error(
                        f"[WATCH] ❌ Error renovando watch "
                        f"#{watch['id']} para {watch['professional_phone']}"
                    )

        except Exception as e:
            logger.error(f"[WATCH] ❌ Error en renew_all_expiring: {e}")
            stats['errors'] += 1

        logger.info(f"[WATCH] 📊 Renovación completada: {stats}")
        return stats

    # =========================================================================
    # DETENER WATCH
    # =========================================================================

    def stop_watch(self, professional_phone: str) -> bool:
        """
        Detiene el watch activo de un profesional.

        Usar cuando el profesional se da de baja o cambia su calendario.

        Args:
            professional_phone: Teléfono del profesional

        Returns:
            True si se detuvo (o no había watch activo), False si hubo error.
        """
        watch = self._get_active_watch(professional_phone)
        if not watch:
            logger.info(
                f"[WATCH] Sin watch activo para {professional_phone}, "
                f"nada que detener"
            )
            return True

        logger.info(
            f"[WATCH] Deteniendo watch #{watch['id']} "
            f"para {professional_phone}"
        )

        ok = self._stop_watch_in_google(watch['channel_id'], watch['resource_id'])
        self._mark_watch_stopped(watch['id'])  # Siempre marcar en BD, incluso si Google falla

        return ok

    # =========================================================================
    # VERIFICAR TOKEN (para validar notificaciones de Google)
    # =========================================================================

    def validate_notification_token(
        self,
        channel_id: str,
        token: str
    ) -> Optional[str]:
        """
        Verifica que una notificación entrante de Google es legítima.

        Google reenvía el token que le pasamos al crear el watch.
        Comparamos ese token con lo que tenemos en BD para asegurarnos
        de que el POST no es un intento de inyección externa.

        Args:
            channel_id: X-Goog-Channel-ID header de la notificación
            token:      X-Goog-Channel-Token header de la notificación

        Returns:
            professional_phone si el token es válido, None si no lo es.
        """
        try:
            with self.db.get_connection() as conn:
                row = conn.execute("""
                    SELECT professional_phone, channel_token
                    FROM calendar_watches
                    WHERE channel_id = ?
                      AND status = 'active'
                """, (channel_id,)).fetchone()

            if not row:
                logger.warning(
                    f"[WATCH] ⚠️ Notificación con channel_id desconocido: "
                    f"{channel_id}"
                )
                return None

            if row['channel_token'] != token:
                logger.warning(
                    f"[WATCH] 🚨 Token inválido para channel {channel_id} — "
                    f"posible intento de inyección"
                )
                return None

            return row['professional_phone']

        except Exception as e:
            logger.error(f"[WATCH] Error validando token: {e}")
            return None

    def get_professional_by_channel(self, channel_id: str) -> Optional[str]:
        """
        Obtiene el professional_phone asociado a un channel_id.

        Usado por el webhook para identificar qué profesional cambió su calendario.

        Args:
            channel_id: X-Goog-Channel-ID header de la notificación

        Returns:
            professional_phone o None si no se encontró.
        """
        try:
            with self.db.get_connection() as conn:
                row = conn.execute("""
                    SELECT professional_phone
                    FROM calendar_watches
                    WHERE channel_id = ?
                      AND status = 'active'
                """, (channel_id,)).fetchone()

            return row['professional_phone'] if row else None

        except Exception as e:
            logger.error(f"[WATCH] Error en get_professional_by_channel: {e}")
            return None

    # =========================================================================
    # PRIVADOS — BD
    # =========================================================================

    def _save_watch(
        self,
        professional_phone: str,
        calendar_id: str,
        channel_id: str,
        resource_id: str,
        channel_token: str,
        expires_at: str,
    ) -> Optional[int]:
        """Persiste un nuevo watch en BD. Retorna el ID insertado."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO calendar_watches
                        (professional_phone, calendar_id, channel_id,
                         resource_id, channel_token, expires_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'active')
                """, (
                    professional_phone,
                    calendar_id,
                    channel_id,
                    resource_id,
                    channel_token,
                    expires_at,
                ))
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"[WATCH] Error guardando watch en BD: {e}")
            return None

    def _get_active_watch(self, professional_phone: str) -> Optional[Dict]:
        """Retorna el watch activo de un profesional, o None."""
        try:
            with self.db.get_connection() as conn:
                row = conn.execute("""
                    SELECT *
                    FROM calendar_watches
                    WHERE professional_phone = ?
                      AND status = 'active'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (professional_phone,)).fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"[WATCH] Error consultando watch activo: {e}")
            return None

    def _get_watch_by_id(self, watch_id: int) -> Optional[Dict]:
        """Retorna un watch por su ID en BD."""
        try:
            with self.db.get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM calendar_watches WHERE id = ?",
                    (watch_id,)
                ).fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"[WATCH] Error consultando watch #{watch_id}: {e}")
            return None

    def _get_expiring_watches(self) -> List[Dict]:
        """
        Retorna watches activos que vencen en las próximas RENEW_BEFORE_DAYS días.
        """
        try:
            threshold = (
                datetime.now(timezone.utc)
                + timedelta(days=self.RENEW_BEFORE_DAYS)
            ).isoformat()

            with self.db.get_connection() as conn:
                rows = conn.execute("""
                    SELECT *
                    FROM calendar_watches
                    WHERE status = 'active'
                      AND expires_at <= ?
                    ORDER BY expires_at ASC
                """, (threshold,)).fetchall()

            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"[WATCH] Error consultando watches por vencer: {e}")
            return []

    def _mark_watch_stopped(self, watch_id: int):
        """Marca un watch como stopped en BD."""
        try:
            with self.db.get_connection() as conn:
                conn.execute("""
                    UPDATE calendar_watches
                    SET status = 'stopped',
                        stopped_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (watch_id,))
        except Exception as e:
            logger.error(f"[WATCH] Error marcando watch #{watch_id} como stopped: {e}")

    # =========================================================================
    # PRIVADOS — GOOGLE API
    # =========================================================================

    def _stop_watch_in_google(self, channel_id: str, resource_id: str) -> bool:
        """
        Llama a channels.stop() en Google Calendar API para cancelar el canal.

        Args:
            channel_id:  ID del canal (el UUID que generamos)
            resource_id: ID del recurso que retornó Google al crear el watch

        Returns:
            True si se detuvo correctamente o si Google retornó 404 (ya expiró).
            False si hubo otro error de API.
        """
        try:
            service = self.calendar_service.calendar_client.service
            service.channels().stop(body={
                'id':         channel_id,
                'resourceId': resource_id,
            }).execute()

            logger.info(
                f"[WATCH] ✅ Watch detenido en Google — channel: {channel_id}"
            )
            return True

        except HttpError as e:
            if e.resp.status == 404:
                # El canal ya expiró o no existe en Google — no es un error real
                logger.info(
                    f"[WATCH] Canal {channel_id} ya no existe en Google "
                    f"(404) — marcando como stopped en BD"
                )
                return True
            logger.error(
                f"[WATCH] ❌ Error deteniendo watch en Google: "
                f"status={e.resp.status}, detail={e}"
            )
            return False

        except Exception as e:
            logger.error(f"[WATCH] ❌ Error inesperado deteniendo watch: {e}")
            return False
