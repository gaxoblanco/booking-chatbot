"""
Scheduler Engine
=================
Ubicación: src/integrations/scheduler/engine.py

APScheduler integrado en el proceso Flask.
Se inicia una sola vez al arrancar la app y corre en background.

Jobs registrados:
    1. reminders        — recordatorios diarios (hora configurable via REMINDER_TIME)
    2. auto_confirm     — confirma citas sin respuesta (1 hora después de reminder)
    3. retry_queue      — reintenta mensajes fallidos (cada hora)
    4. calendar_sync    — sincroniza cancelaciones desde Google Calendar (diario)
    5. watches          — renueva watch channels de Google Calendar (diario)
    6. waitlist         — procesa lista de espera / ofertas expiradas (diario)

Configuración:
    REMINDER_TIME=17:30          → horario del job de recordatorios (HH:MM)
    TIMEZONE=America/Argentina/Buenos_Aires
    FLASK_ENV=development        → en development los jobs no corren automáticamente
                                   (se disparan solo manualmente via comando secreto)

Uso:
    # En whatsapp_handler.py — llamar una sola vez al arrancar
    from src.integrations.scheduler.engine import scheduler_engine
    scheduler_engine.start()

    # Para detener (al cerrar la app)
    scheduler_engine.stop()
"""

import logging
import os
from datetime import datetime
from typing import Dict

logger = logging.getLogger(__name__)


class SchedulerEngine:
    """
    Wrapper sobre APScheduler.
    Registra y gestiona todos los jobs del sistema.
    """

    def __init__(self):
        self._scheduler = None
        self._started   = False

    # =========================================================================
    # ARRANQUE Y DETENCIÓN
    # =========================================================================

    def start(self) -> None:
        """
        Inicia el scheduler y registra todos los jobs.
        Solo corre jobs automáticos en producción.
        En development los jobs existen pero no se disparan solos.
        """
        if self._started:
            logger.warning("[SCHEDULER] Ya estaba iniciado — ignorando")
            return

        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.executors.pool import ThreadPoolExecutor
            import pytz

            tz_name  = os.getenv("TIMEZONE", "America/Argentina/Buenos_Aires")
            timezone = pytz.timezone(tz_name)

            executors = {
                # Un solo worker — los jobs son secuenciales, no compiten por la BD
                "default": ThreadPoolExecutor(max_workers=1)
            }

            job_defaults = {
                "coalesce":       True,   # si se perdió una ejecución, corre solo una vez
                "max_instances":  1,      # nunca dos instancias del mismo job en paralelo
                "misfire_grace_time": 300 # acepta hasta 5 min de retraso antes de saltear
            }

            self._scheduler = BackgroundScheduler(
                executors=executors,
                job_defaults=job_defaults,
                timezone=timezone,
            )

            # Registrar jobs
            self._register_jobs(timezone)

            self._scheduler.start()
            self._started = True

            env = os.getenv("FLASK_ENV", "development")
            logger.info("=" * 60)
            logger.info("✅ SCHEDULER iniciado")
            logger.info(f"   Entorno:  {env}")
            logger.info(f"   Timezone: {tz_name}")
            logger.info(f"   Jobs automáticos: {'✅ activos' if env == 'production' else '⏸️  pausados (development)'}")
            logger.info("=" * 60)

        except ImportError:
            logger.error(
                "[SCHEDULER] ❌ APScheduler no instalado. "
                "Agregá 'apscheduler' y 'pytz' al requirements.txt"
            )
        except Exception as e:
            logger.error(f"[SCHEDULER] ❌ Error al iniciar: {e}")
            import traceback
            traceback.print_exc()

    def stop(self) -> None:
        """Detiene el scheduler limpiamente al cerrar la app."""
        if self._scheduler and self._started:
            self._scheduler.shutdown(wait=False)
            self._started = False
            logger.info("[SCHEDULER] ⏹️  Detenido")

    # =========================================================================
    # REGISTRO DE JOBS
    # =========================================================================

    def _register_jobs(self, timezone) -> None:
        """
        Registra los 6 jobs con sus horarios.
        En development: todos en modo 'date' con fecha pasada (no corren solos).
        En production: cron real.
        """
        env = os.getenv("FLASK_ENV", "development")
        is_prod = (env == "production")

        # Parsear horario de recordatorios desde .env
        reminder_h, reminder_m = self._parse_reminder_time()

        if is_prod:
            # ── 1. Recordatorios diarios ─────────────────────────────────────
            self._scheduler.add_job(
                func     = job_reminders,
                trigger  = "cron",
                hour     = reminder_h,
                minute   = reminder_m,
                timezone = timezone,
                id       = "reminders",
                name     = "Recordatorios diarios",
                replace_existing = True,
            )

            # ── 2. Auto-confirmar citas sin respuesta ─────────────────────────
            # Corre 3 horas después de los recordatorios
            auto_h = (reminder_h + 3) % 24
            self._scheduler.add_job(
                func     = job_auto_confirm,
                trigger  = "cron",
                hour     = auto_h,
                minute   = reminder_m,
                timezone = timezone,
                id       = "auto_confirm",
                name     = "Auto-confirmar citas sin respuesta",
                replace_existing = True,
            )

            # ── 3. Cola de reintentos ─────────────────────────────────────────
            self._scheduler.add_job(
                func     = job_retry_queue,
                trigger  = "interval",
                hours    = 1,
                timezone = timezone,
                id       = "retry_queue",
                name     = "Cola de reintentos de mensajes",
                replace_existing = True,
            )

            # ── 4. Sync cancelaciones Google Calendar ─────────────────────────
            self._scheduler.add_job(
                func     = job_calendar_sync,
                trigger  = "cron",
                hour     = reminder_h,
                minute   = reminder_m + 1 if reminder_m < 59 else 0,
                timezone = timezone,
                id       = "calendar_sync",
                name     = "Sync cancelaciones Google Calendar",
                replace_existing = True,
            )

            # ── 5. Renovación watch channels ──────────────────────────────────
            self._scheduler.add_job(
                func     = job_watches,
                trigger  = "cron",
                hour     = reminder_h,
                minute   = reminder_m + 2 if reminder_m < 58 else 1,
                timezone = timezone,
                id       = "watches",
                name     = "Renovación watch channels Google Calendar",
                replace_existing = True,
            )

            # ── 6. Waitlist / ofertas expiradas ───────────────────────────────
            self._scheduler.add_job(
                func     = job_waitlist,
                trigger  = "cron",
                hour     = reminder_h,
                minute   = reminder_m + 3 if reminder_m < 57 else 2,
                timezone = timezone,
                id       = "waitlist",
                name     = "Waitlist — ofertas expiradas",
                replace_existing = True,
            )

        else:
            # Development: registrar jobs sin trigger activo
            # Solo se ejecutan via trigger_job() manual
            for job_id, job_func, job_name in [
                ("reminders",    job_reminders,    "Recordatorios diarios"),
                ("auto_confirm", job_auto_confirm, "Auto-confirmar sin respuesta"),
                ("retry_queue",  job_retry_queue,  "Cola de reintentos"),
                ("calendar_sync",job_calendar_sync,"Sync Google Calendar"),
                ("watches",      job_watches,      "Renovación watches"),
                ("waitlist",     job_waitlist,      "Waitlist"),
            ]:
                # Fecha en el pasado → nunca se dispara solo
                self._scheduler.add_job(
                    func     = job_func,
                    trigger  = "date",
                    run_date = "2000-01-01 00:00:00",
                    id       = job_id,
                    name     = job_name,
                    replace_existing = True,
                )

        logger.info(f"[SCHEDULER] ✅ {6} jobs registrados")

    # =========================================================================
    # DISPARO MANUAL
    # =========================================================================

    def trigger_job(self, job_id: str) -> Dict:
        """
        Dispara un job manualmente de forma inmediata.
        Usado por el comando secreto del bot y para testing.

        Args:
            job_id: 'reminders' | 'auto_confirm' | 'retry_queue' |
                    'calendar_sync' | 'watches' | 'waitlist'

        Returns:
            Dict con resultado de la ejecución
        """
        JOB_MAP = {
            "reminders":    job_reminders,
            "auto_confirm": job_auto_confirm,
            "retry_queue":  job_retry_queue,
            "calendar_sync":job_calendar_sync,
            "watches":      job_watches,
            "waitlist":     job_waitlist,
        }

        if job_id not in JOB_MAP:
            return {
                "success": False,
                "error":   f"Job desconocido: '{job_id}'. Opciones: {list(JOB_MAP.keys())}"
            }

        logger.info(f"[SCHEDULER] 🔔 Disparo manual: {job_id}")
        try:
            result = JOB_MAP[job_id]()
            return {"success": True, "job": job_id, **result}
        except Exception as e:
            logger.error(f"[SCHEDULER] ❌ Error en {job_id}: {e}")
            return {"success": False, "job": job_id, "error": str(e)}

    # =========================================================================
    # ESTADO
    # =========================================================================

    def get_status(self) -> Dict:
        """
        Retorna estado de todos los jobs.
        Usado por el health check del bot.
        """
        if not self._scheduler or not self._started:
            return {"running": False, "jobs": {}}

        jobs = {}
        for job in self._scheduler.get_jobs():
            jobs[job.id] = {
                "name":     job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            }

        return {
            "running": True,
            "env":     os.getenv("FLASK_ENV", "development"),
            "jobs":    jobs,
        }

    # =========================================================================
    # HELPERS
    # =========================================================================

    @staticmethod
    def _parse_reminder_time() -> tuple:
        """Parsea REMINDER_TIME del .env. Default: 17:30."""
        raw = os.getenv("REMINDER_TIME", "17:30")
        try:
            h, m = raw.split(":")
            return int(h), int(m)
        except Exception:
            logger.warning(
                f"[SCHEDULER] REMINDER_TIME inválido: '{raw}' — usando 17:30"
            )
            return 17, 30


# =============================================================================
# FUNCIONES DE JOB — llamadas por APScheduler
# Cada función es liviana: delega al servicio correspondiente y loguea.
# =============================================================================

def job_reminders() -> Dict:
    """Recordatorios diarios — delegado al ReminderIntegrationService."""
    logger.info("[JOB] 🔔 Iniciando: recordatorios diarios")
    try:
        from src.integrations.reminder import reminder_integration_service
        return reminder_integration_service.run_send_cycle()
    except Exception as e:
        logger.error(f"[JOB] ❌ Error en recordatorios: {e}")
        return {"sent": 0, "checked": 0, "errors": 1, "error_detail": str(e)}


def job_auto_confirm() -> Dict:
    """Auto-confirmación por timeout — delegado al ReminderIntegrationService."""
    logger.info("[JOB] 🔔 Iniciando: auto-confirm")
    try:
        from src.integrations.reminder import reminder_integration_service
        return reminder_integration_service.run_confirm_cycle()
    except Exception as e:
        logger.error(f"[JOB] ❌ Error en auto-confirm: {e}")
        return {"confirmed": 0, "errors": 1, "error_detail": str(e)}
    
def job_retry_queue() -> Dict:
    """Reintenta mensajes de WhatsApp que fallaron en el envío anterior."""
    logger.info("[JOB] 🔔 Iniciando: retry queue")
    try:
        from src.core.message_sender import message_sender
        stats = message_sender.process_retry_queue()
        logger.info(f"[JOB] ✅ Retry queue: {stats}")
        return stats
    except Exception as e:
        logger.error(f"[JOB] ❌ Error en retry queue: {e}")
        return {"retried": 0, "errors": 1, "error_detail": str(e)}


def job_calendar_sync() -> Dict:
    """
    Sincroniza citas contra Google Calendar.
    Detecta cancelaciones que no llegaron por webhook y notifica pacientes.
    Importa los servicios directamente — no pasa por daily_reminder_job.
    """
    logger.info("[JOB] 🔔 Iniciando: calendar sync")
    try:
        from src.database.database import db
        from src.integrations.appointment_calendar_service import AppointmentCalendarService
        from src.services.cancellation_notifier import cancellation_notifier
        from src.services.professional_service import professional_service
        from datetime import datetime, timedelta

        stats = {
            "professionals_checked": 0,
            "appointments_synced":   0,
            "cancellations_found":   0,
            "notifications_sent":    0,
            "errors":                0,
        }

        professionals = professional_service.get_active_professionals_with_calendar()
        stats["professionals_checked"] = len(professionals)

        if not professionals:
            logger.info("[JOB] ℹ️  Sin profesionales con calendario configurado")
            return stats

        calendar_service = AppointmentCalendarService(db)
        today  = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        for prof in professionals:
            prof_phone = prof.get("phone")
            try:
                appointments = db.get_appointments_by_professional(
                    professional_phone=prof_phone,
                    status="confirmada",
                    from_date=today,
                )
                to_sync = [
                    a for a in appointments
                    if a.get("google_event_id") and a.get("appointment_date", "") <= future
                ]

                for apt in to_sync:
                    apt_id        = apt["id"]
                    status_before = apt["status"]   # ← guardamos antes del sync
                    try:
                        success = calendar_service.sync_appointment_from_google(apt_id)
                        if not success:
                            continue

                        stats["appointments_synced"] += 1
                        apt_updated = db.get_appointment(apt_id)
                        if not apt_updated:
                            continue

                        # Comparamos status_before (confirmada) contra status_after
                        if (
                            apt_updated.get("status") == "cancelada_profesional"
                            and status_before == "confirmada"
                            and not apt_updated.get("cancellation_notified", False)
                        ):
                            stats["cancellations_found"] += 1
                            result = cancellation_notifier.notify_patient(apt_id)
                            if result.get("success"):
                                stats["notifications_sent"] += 1
                            else:
                                stats["errors"] += 1

                    except Exception as e:
                        logger.error(f"[JOB] ❌ Error sincronizando cita #{apt_id}: {e}")
                        stats["errors"] += 1

            except Exception as e:
                logger.error(f"[JOB] ❌ Error procesando profesional {prof_phone}: {e}")
                stats["errors"] += 1

        logger.info(f"[JOB] ✅ Calendar sync: {stats}")
        return stats

    except Exception as e:
        logger.error(f"[JOB] ❌ Error en calendar sync: {e}")
        return {"cancellations_found": 0, "errors": 1, "error_detail": str(e)}

def job_watches() -> Dict:
    """
    Renueva watch channels de Google Calendar que vencen en 24 horas.

    Importa WatchManager directamente — no pasa por daily_reminder_job
    para evitar ejecutar el pipeline completo del cron CLI.
    """
    logger.info("[JOB] 🔔 Iniciando: watch renewal")
    try:
        from src.integrations.google_calendar_service import GoogleCalendarService
        from src.integrations.google_calendar_service.watch_manager import WatchManager
        from src.database.database import db

        webhook_url      = os.getenv("GOOGLE_CALENDAR_WEBHOOK_URL", "")
        calendar_service = GoogleCalendarService()
        watch_mgr        = WatchManager(calendar_service, db, webhook_url)

        stats = watch_mgr.renew_all_expiring()
        logger.info(f"[JOB] ✅ Watches: {stats}")
        return stats

    except Exception as e:
        logger.error(f"[JOB] ❌ Error en watch renewal: {e}")
        return {"renewed": 0, "errors": 1, "error_detail": str(e)}


def job_waitlist() -> Dict:
    """Procesa ofertas expiradas de la lista de espera."""
    logger.info("[JOB] 🔔 Iniciando: waitlist")
    try:
        from src.services.waitlist_service import waitlist_service
        stats = waitlist_service.process_expired_offers()
        logger.info(f"[JOB] ✅ Waitlist: {stats}")
        return stats
    except Exception as e:
        logger.error(f"[JOB] ❌ Error en waitlist: {e}")
        return {"processed": 0, "errors": 1, "error_detail": str(e)}


# =============================================================================
# INSTANCIA GLOBAL
# =============================================================================
scheduler_engine = SchedulerEngine()