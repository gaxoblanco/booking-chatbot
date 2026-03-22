"""
CRON Job - Recordatorios Diarios
=================================

Ejecuta el servicio de recordatorios todos los días a las 17:30.

Configuración de Crontab:
    30 17 * * * cd /app && python -m src.cron.daily_reminder_job >> /var/log/reminders.log 2>&1

Para Docker:
    Agregar al docker-compose.yml un servicio scheduler o usar cron del host.

Author: Salud Conecta
"""

import sys
import os
from datetime import datetime
from src.services.waitlist_service import waitlist_service

# Agregar path del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.reminder_service import reminder_service
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Función principal del CRON job."""
    logger.info("=" * 70)
    logger.info(f"🔔 CRON JOB INICIADO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)
    
    try:
        # Ejecutar servicio de recordatorios
        stats = reminder_service.send_daily_reminders()

        # Procesar ofertas de waitlist expiradas
        # Limpia ofertas sin respuesta y reintenta la cascada
        logger.info("─" * 70)
        logger.info("🔄 Procesando ofertas de waitlist expiradas...")
        waitlist_stats = waitlist_service.process_expired_offers()
        logger.info(f"📊 Waitlist: {waitlist_stats}")

        # Log final
        logger.info("=" * 70)
        logger.info(f"✅ CRON JOB COMPLETADO")
        logger.info(f"📊 Recordatorios: {stats}")
        logger.info(f"📊 Waitlist expiradas: {waitlist_stats}")
        logger.info("=" * 70)

        # Exit code basado en errores totales
        total_errors = stats.get('errors', 0) + waitlist_stats.get('errors', 0)
        if total_errors > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"❌ ERROR CRÍTICO EN CRON JOB: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
