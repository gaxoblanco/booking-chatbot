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
        
        # Log final
        logger.info("=" * 70)
        logger.info(f"✅ CRON JOB COMPLETADO")
        logger.info(f"📊 Estadísticas: {stats}")
        logger.info("=" * 70)
        
        # Exit code basado en errores
        if stats.get('errors', 0) > 0:
            sys.exit(1)  # Error code
        else:
            sys.exit(0)  # Success
            
    except Exception as e:
        logger.error(f"❌ ERROR CRÍTICO EN CRON JOB: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
