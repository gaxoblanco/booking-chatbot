"""
Setup Calendar Watches
======================
Ubicación: scripts/setup_calendar_watches.py

Script de setup único: registra watch channels de Google Calendar
para todos los profesionales activos que tengan calendar_id configurado.

Ejecutar:
    1. La primera vez que se despliega el Issue 7
    2. Después de agregar nuevos profesionales al sistema
    3. Si los watches se perdieron por algún motivo (reset de BD, etc.)

Es idempotente: si un profesional ya tiene watch activo, lo renueva.

Uso:
    docker exec -it whatsapp-demo python scripts/setup_calendar_watches.py

    # Con verbose:
    docker exec -it whatsapp-demo python scripts/setup_calendar_watches.py --verbose

Prerequisitos:
    - GOOGLE_CALENDAR_WEBHOOK_URL en .env apuntando a una URL HTTPS pública
    - Service Account con acceso a los calendarios de los profesionales
    - Los profesionales deben tener calendar_id en BD
"""

import sys
import os
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main(verbose: bool = False):
    print()
    print("=" * 65)
    print("  SETUP CALENDAR WATCHES — Issue 7")
    print("=" * 65)

    # ── Validar prerequisito: URL del webhook ────────────────────────────────
    webhook_url = os.getenv('GOOGLE_CALENDAR_WEBHOOK_URL', '').strip()

    if not webhook_url:
        print("\n❌ GOOGLE_CALENDAR_WEBHOOK_URL no está configurada en .env")
        print("   Agregar:")
        print("   GOOGLE_CALENDAR_WEBHOOK_URL=https://tu-dominio.com/google-calendar/webhook")
        print()
        sys.exit(1)

    if not webhook_url.startswith('https://'):
        print(f"\n⚠️  GOOGLE_CALENDAR_WEBHOOK_URL debe ser HTTPS:")
        print(f"   Actual: {webhook_url}")
        print(f"   Google rechaza URLs sin SSL")
        print()
        sys.exit(1)

    print(f"\n📡 Webhook URL: {webhook_url}")

    # ── Inicializar servicios ────────────────────────────────────────────────
    try:
        from src.database.database import db
        from src.integrations.google_calendar_service import GoogleCalendarService
        from src.integrations.google_calendar_service.watch_manager import WatchManager

        calendar_service = GoogleCalendarService()
        watch_mgr        = WatchManager(calendar_service, db, webhook_url)
        print("✅ Servicios inicializados\n")

    except Exception as e:
        print(f"\n❌ Error inicializando servicios: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # ── Obtener profesionales activos con calendario ─────────────────────────
    try:
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

    except Exception as e:
        print(f"❌ Error consultando profesionales: {e}")
        sys.exit(1)

    if not professionals:
        print("⚠️  No hay profesionales activos con calendar_id configurado.")
        print("   Verificar que los profesionales tienen calendar_id en la BD.")
        print()
        sys.exit(0)

    print(f"👥 Profesionales a registrar: {len(professionals)}")
    for p in professionals:
        print(f"   • {p['name']} ({p['phone']}) → {p['calendar_id']}")

    print()

    # ── Registrar watch por profesional ─────────────────────────────────────
    stats = {'ok': 0, 'error': 0, 'skipped': 0}

    for prof in professionals:
        phone       = prof['phone']
        name        = prof['name']
        calendar_id = prof['calendar_id']

        print(f"─" * 65)
        print(f"👤 {name} ({phone})")
        print(f"   📅 Calendar: {calendar_id}")

        try:
            result = watch_mgr.create_watch(
                professional_phone = phone,
                calendar_id        = calendar_id,
            )

            if result:
                print(f"   ✅ Watch creado")
                print(f"      channel_id: {result['channel_id'][:16]}...")
                print(f"      expires_at: {result['expires_at'][:19]}")
                stats['ok'] += 1
            else:
                print(f"   ❌ Error creando watch (ver logs arriba)")
                stats['error'] += 1

        except Exception as e:
            print(f"   ❌ Excepción: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
            stats['error'] += 1

    # ── Resumen ──────────────────────────────────────────────────────────────
    print()
    print("=" * 65)
    print("  RESUMEN")
    print("=" * 65)
    print(f"  ✅ Exitosos:  {stats['ok']}")
    print(f"  ❌ Errores:   {stats['error']}")
    print(f"  ⏭️  Saltados:  {stats['skipped']}")
    print()

    if stats['error'] > 0:
        print("⚠️  Algunos watches no se pudieron crear.")
        print("   Causas comunes:")
        print("   • GOOGLE_CALENDAR_WEBHOOK_URL no es accesible desde internet")
        print("   • La Service Account no tiene acceso al calendario del profesional")
        print("   • El calendar_id es incorrecto")
        print()
        sys.exit(1)
    else:
        print("✅ Todos los watches registrados correctamente.")
        print("   Google enviará notificaciones push cuando los profesionales")
        print("   modifiquen sus calendarios.")
        print()
        print("ℹ️  Los watches se renuevan automáticamente cada día via CRON.")
        print()
        sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Registra watch channels de Google Calendar para todos los profesionales"
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Mostrar stack traces completos en caso de error'
    )
    args = parser.parse_args()
    main(verbose=args.verbose)
