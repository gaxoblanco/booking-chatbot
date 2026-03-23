"""
CRON Job - Recordatorios Diarios
=================================

Ejecuta diariamente a las 17:30. Corre 4 servicios en orden:

    1. Recordatorios      — avisa a pacientes de sus turnos del día siguiente
    2. Waitlist           — limpia ofertas expiradas y reintenta la cascada
    3. Sync cancelaciones — detecta turnos cancelados desde Google Calendar
                            y notifica a los pacientes afectados
                            (fallback por si el push webhook no llegó)
    4. Watches            — renueva los watch channels de Google Calendar
                            que vencen en las próximas 24 horas

Configuración de Crontab:
    30 17 * * * cd /app && python -m src.cron.daily_reminder_job >> /var/log/reminders.log 2>&1

Para Docker (recomendado):
    docker exec whatsapp-demo python -m src.cron.daily_reminder_job

Author: Salud Conecta
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.reminder_service import reminder_service
from src.services.waitlist_service import waitlist_service
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_cancellation_sync() -> dict:
    """
    Fallback de sync: detecta citas canceladas desde Google Calendar
    que no fueron procesadas por el webhook push (latencia, reinicio, etc.)

    Recorre todos los profesionales activos con calendar_id configurado,
    sincroniza sus citas confirmadas de los próximos 7 días contra Google,
    y notifica a los pacientes de cualquier cancelación no notificada.

    Returns:
        {
            'professionals_checked': int,
            'appointments_synced':   int,
            'cancellations_found':   int,
            'notifications_sent':    int,
            'errors':                int,
        }
    """
    from src.database.database import db
    from src.integrations.appointment_calendar_service import AppointmentCalendarService
    from src.services.cancellation_notifier import cancellation_notifier
    from datetime import datetime, timedelta

    stats = {
        'professionals_checked': 0,
        'appointments_synced':   0,
        'cancellations_found':   0,
        'notifications_sent':    0,
        'errors':                0,
    }

    try:
        # Obtener profesionales activos con calendario configurado
        with db.get_connection() as conn:
            rows = conn.execute("""
                SELECT phone, name, calendar_id
                FROM professionals
                WHERE is_active = 1
                  AND calendar_id IS NOT NULL
                  AND calendar_id != ''
                ORDER BY name
            """).fetchall()

        professionals = [dict(r) for r in rows]
        stats['professionals_checked'] = len(professionals)

        if not professionals:
            logger.info("[SYNC-CRON] ℹ️  Sin profesionales con calendario configurado")
            return stats

        logger.info(
            f"[SYNC-CRON] 🔄 Sincronizando {len(professionals)} profesional(es)"
        )

        calendar_service = AppointmentCalendarService(db)
        today            = datetime.now().strftime("%Y-%m-%d")
        in_7_days        = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        for prof in professionals:
            prof_phone = prof['phone']
            try:
                # Citas confirmadas de los próximos 7 días con google_event_id
                appointments = db.get_appointments_by_professional(
                    professional_phone = prof_phone,
                    status             = 'confirmada',
                    from_date          = today,
                )

                to_sync = [
                    a for a in appointments
                    if a.get('google_event_id')
                    and a.get('appointment_date', '') <= in_7_days
                ]

                for apt in to_sync:
                    apt_id        = apt['id']
                    status_before = apt['status']
                    try:
                        ok = calendar_service.sync_appointment_from_google(apt_id)
                        if not ok:
                            continue

                        stats['appointments_synced'] += 1

                        apt_updated  = db.get_appointment(apt_id)
                        status_after = apt_updated.get('status', '') if apt_updated else ''

                        # ¿Recién cancelada por el profesional y aún no notificada?
                        if (
                            status_after  == 'cancelada_profesional'
                            and status_before == 'confirmada'
                            and apt_updated
                            and not apt_updated.get('cancellation_notified', False)
                        ):
                            stats['cancellations_found'] += 1
                            logger.info(
                                f"[SYNC-CRON] 🔴 Cita #{apt_id} cancelada "
                                f"por {prof['name']} — notificando paciente"
                            )

                            result = cancellation_notifier.notify_patient(apt_id)
                            if result.get('success'):
                                stats['notifications_sent'] += 1
                            else:
                                stats['errors'] += 1

                    except Exception as e:
                        logger.error(
                            f"[SYNC-CRON] ❌ Error sincronizando cita #{apt_id}: {e}"
                        )
                        stats['errors'] += 1

            except Exception as e:
                logger.error(
                    f"[SYNC-CRON] ❌ Error procesando profesional {prof_phone}: {e}"
                )
                stats['errors'] += 1

    except Exception as e:
        logger.error(f"[SYNC-CRON] ❌ Error crítico en run_cancellation_sync: {e}")
        stats['errors'] += 1

    logger.info(f"[SYNC-CRON] 📊 Sync completado: {stats}")
    return stats


def run_watch_renewal() -> dict:
    """
    Renueva los watch channels de Google Calendar que vencen
    en las próximas 24 horas.

    Los watches expiran cada 7 días. Sin renovación, Google deja
    de enviar notificaciones push y el Issue 7 deja de funcionar
    en tiempo real (el sistema cae de nuevo al modo pull del CRON).

    Returns:
        { 'checked': int, 'renewed': int, 'errors': int }
    """
    try:
        from src.integrations.google_calendar_service import GoogleCalendarService
        from src.integrations.google_calendar_service.watch_manager import WatchManager
        from src.database.database import db

        webhook_url      = os.getenv('GOOGLE_CALENDAR_WEBHOOK_URL', '')
        calendar_service = GoogleCalendarService()
        watch_mgr        = WatchManager(calendar_service, db, webhook_url)

        stats = watch_mgr.renew_all_expiring()
        logger.info(f"[WATCHES] 📊 Renovación completada: {stats}")
        return stats

    except Exception as e:
        logger.error(f"[WATCHES] ❌ Error en run_watch_renewal: {e}")
        return {'checked': 0, 'renewed': 0, 'errors': 1}


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Función principal del CRON job."""
    logger.info("=" * 70)
    logger.info(f"🔔 CRON JOB INICIADO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)

    total_errors = 0

    try:
        # ── 0. Cola de reintentos ────────────────────────────────────────────
        logger.info("─" * 70)
        logger.info("0️⃣  Cola de reintentos de mensajes")
        logger.info("─" * 70)
        from src.core.message_sender import message_sender
        retry_stats = message_sender.process_retry_queue()
        logger.info(f"📊 Reintentos: {retry_stats}")
        total_errors += retry_stats.get('errors', 0)
        
        # ── 1. Recordatorios diarios ─────────────────────────────────────────
        logger.info("─" * 70)
        logger.info("1️⃣  Recordatorios diarios")
        logger.info("─" * 70)
        reminder_stats = reminder_service.send_daily_reminders()
        logger.info(f"📊 Recordatorios: {reminder_stats}")
        total_errors += reminder_stats.get('errors', 0)

        # ── 2. Waitlist — limpiar ofertas expiradas ──────────────────────────
        logger.info("─" * 70)
        logger.info("2️⃣  Waitlist — ofertas expiradas")
        logger.info("─" * 70)
        waitlist_stats = waitlist_service.process_expired_offers()
        logger.info(f"📊 Waitlist: {waitlist_stats}")
        total_errors += waitlist_stats.get('errors', 0)

        # ── 3. Sync de cancelaciones (fallback del webhook) ──────────────────
        logger.info("─" * 70)
        logger.info("3️⃣  Sync cancelaciones Google Calendar")
        logger.info("─" * 70)
        sync_stats = run_cancellation_sync()
        logger.info(f"📊 Sync: {sync_stats}")
        total_errors += sync_stats.get('errors', 0)

        # ── 4. Renovación de watch channels ─────────────────────────────────
        logger.info("─" * 70)
        logger.info("4️⃣  Renovación de watch channels")
        logger.info("─" * 70)
        watch_stats = run_watch_renewal()
        logger.info(f"📊 Watches: {watch_stats}")
        total_errors += watch_stats.get('errors', 0)

        # ── Resumen final ────────────────────────────────────────────────────
        logger.info("=" * 70)
        logger.info("✅ CRON JOB COMPLETADO")
        logger.info(f"   Recordatorios:  enviados={reminder_stats.get('sent', 0)}, "
                    f"errores={reminder_stats.get('errors', 0)}")
        logger.info(f"   Waitlist:       procesadas={waitlist_stats.get('processed', 0)}, "
                    f"errores={waitlist_stats.get('errors', 0)}")
        logger.info(f"   Sync Calendar:  sincronizadas={sync_stats.get('appointments_synced', 0)}, "
                    f"cancelaciones={sync_stats.get('cancellations_found', 0)}, "
                    f"notificaciones={sync_stats.get('notifications_sent', 0)}")
        logger.info(f"   Watches:        renovados={watch_stats.get('renewed', 0)}, "
                    f"errores={watch_stats.get('errors', 0)}")
        logger.info(f"   Total errores:  {total_errors}")
        logger.info("=" * 70)

        sys.exit(1 if total_errors > 0 else 0)

    except Exception as e:
        logger.error(f"❌ ERROR CRÍTICO EN CRON JOB: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
